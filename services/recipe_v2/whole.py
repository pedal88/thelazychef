"""The whole dish on the cooking screen: the timeline and the metro map (RECIPE_VISUALIZATIONS.md 9.15).

Ported from the large-screen prototype (vTimelineW and vMetroV in docs/prototypes/stor-skjerm.html).
Both are drawn from the plan, so they show the same order and minutes as the method list and the cards;
the river delta (delta.py) is the third view. Step numbers are the method list's numbers everywhere.
The page marks the step you are on (static/js/steps.js).
"""


def _header(s):
    """A step with no ingredients and no inputs ("line the tin"): not a station of its own."""
    return not s.get('uses') and not s.get('after')


def timeline(v2, sch, comps):
    """One row per step in planned order, with its active time, its standing time and how long its result
    waits before it is used. Positions are percentages of the total time."""
    by = {s['local_id']: s for s in v2.get('steps') or []}
    order = [sid for sid in sch['order'] if sid in by]
    if not order:
        return None
    total = max(1, sch['T'])

    def pct(m):
        return round(m / total * 100, 3)

    rows = []
    for n, sid in enumerate(order, 1):
        s, p = by[sid], sch['plan'][sid]
        active, standing = s.get('active_minutes') or 0, s.get('passive_minutes') or 0
        waits = max(0, (p.get('use') or p['end']) - p['end'])
        rows.append({
            'id': sid, 'no': n, 'short': s['short'], 'phase': s['phase'], 'component': comps.get(s['component_id'], ''),
            'start': p['start'], 'a_end': p['a_end'], 'end': p['end'],
            'active': {'left': pct(p['start']), 'width': pct(active)} if active else None,
            'standing': {'left': pct(p['a_end']), 'width': pct(standing)} if standing else None,
            'waits': {'left': pct(p['end']), 'width': pct(waits), 'over': sid in (sch.get('over') or [])} if waits else None,
        })
    busy, free = [], []
    me = sch.get('me') or []
    for k, (x, y) in enumerate(me):
        busy.append({'left': pct(x), 'width': pct(y - x)})
        if k + 1 < len(me) and me[k + 1][0] - y >= 4:
            gap = me[k + 1][0] - y
            free.append({'left': pct(y), 'width': pct(gap), 'minutes': gap, 'from': y, 'to': me[k + 1][0], 'label': gap / total > 0.09})
    step = 30 if total > 150 else 15 if total > 70 else 10
    return {
        'total': total, 'rows': rows, 'busy': busy, 'free': free,
        'ticks': [{'left': pct(t), 'label': t} for t in range(0, total + 1, step)],
        'phases': [{'x': round(x / total, 4), 'label': label, 'right': x / total > 0.9}
                   for x, label in ((sch.get('cook_start'), 'cook'), (sch.get('serve_start'), 'serve')) if x and 0 < x < total],
    }


# The metro map of the one-page flow (25.10.2026, Pål; RECIPE_VISUALIZATIONS.md 9.17): drawn as a real transit map,
# with the distance down the map in minutes.

def _metro_base(v2, sch, comps):
    by = {s['local_id']: s for s in v2.get('steps') or []}
    order = [sid for sid in sch['order'] if sid in by]
    number = {sid: n for n, sid in enumerate(order, 1)}
    stations = [sid for sid in order if not _header(by[sid])]
    if not stations:
        return None
    lanes = list(dict.fromkeys(by[sid]['component_id'] for sid in stations))
    lane_of = {sid: lanes.index(by[sid]['component_id']) for sid in stations}
    edges = [(a, sid) for sid in stations for a in by[sid].get('after') or [] if a in lane_of]
    final = next((sid for sid in stations if not any(sid == a for a, _ in edges)), stations[-1])

    def minutes(s):
        active, standing = s.get('active_minutes') or 0, s.get('passive_minutes') or 0
        return f"{active} min" + (f" + {standing}" if standing else '') if active else (f"{standing} min" if standing else '')

    info = {sid: {'id': sid, 'no': number[sid], 'short': by[sid]['short'], 'phase': by[sid]['phase'], 'lane': lane_of[sid],
                  'start': sch['plan'][sid]['start'], 'a_end': sch['plan'][sid]['a_end'], 'end': sch['plan'][sid]['end'],
                  'final': sid == final, 'time': minutes(by[sid]),
                  # where two parts of the dish meet: a step that takes something from another line
                  'merge': any(lane_of[a] != lane_of[sid] for a, b in edges if b == sid)} for sid in stations}
    return {'stations': stations, 'lanes': [{'name': comps.get(c, c), 'n': k % 4} for k, c in enumerate(lanes)],
            'edges': edges, 'info': info, 'total': max(1, sch['T'])}


def _curve(ax, ay, bx, by_, bend=0.6):
    if ax == bx:
        return f'M{ax:g} {ay:g} V{by_:g}'
    dy = (by_ - ay) * bend
    return f'M{ax:g} {ay:g} C{ax:g} {ay + dy:g} {bx:g} {by_ - dy:g} {bx:g} {by_:g}'


BREAK_AFTER = 20  # minutes without a new station before the stretch is cut short with a zigzag
BREAK_KEEP = 8    # how many minutes such a stretch is drawn as


def metro_map(v2, sch, comps):
    """The metro map for the one-page flow, top to bottom: a line per part of the dish in colours of its own, white
    stations, a wide station where parts meet, the end station large. Down the map is time: a station sits at the
    minute it starts, never closer to the one before than a name needs. A stretch of more than BREAK_AFTER minutes
    with no new station (the chicken marinating for an hour) is drawn as BREAK_KEEP minutes and marked with a
    zigzag that says how long it really is. Standing time is a dashed stretch beside its station."""
    b = _metro_base(v2, sch, comps)
    if not b:
        return None
    st, info, n_lanes = b['stations'], b['info'], len(b['lanes'])
    total = b['total']
    # The lines 40 px apart, so it is plain which line belongs to which part (25.10.2026; was 22), 48 with three
    # lines or fewer
    top, gap_px, x0 = 30, 34, 20
    lane_w = 48 if n_lanes <= 3 else 40
    per_min = max(4.0, min(9.0, 640 / max(30, min(total, 120))))

    # Where each minute is drawn: a list of (minute, y) points, with the long stretches shortened
    ys, breaks, points = {}, [], []
    last_m = last_y = None
    for sid in st:
        m = info[sid]['start']
        if last_m is None:
            y = top + m * per_min
        else:
            gap = m - last_m
            if gap > BREAK_AFTER:
                drawn = BREAK_KEEP * per_min
                breaks.append({'y': round(last_y + drawn / 2, 1), 'minutes': gap, 'from': last_m, 'to': m})
                y = last_y + max(gap_px, drawn)
            else:
                y = last_y + max(gap_px if gap else gap_px, gap * per_min)
        if last_m is None or m != last_m or y != last_y:
            points.append((m, y))
        ys[sid], last_m, last_y = y, m, y

    def y_at(minute):
        if minute <= points[0][0]:
            return points[0][1] - (points[0][0] - minute) * per_min
        for (m0, y0), (m1, y1) in zip(points, points[1:]):
            if m0 <= minute <= m1:
                return y0 if m1 == m0 else y0 + (y1 - y0) * (minute - m0) / (m1 - m0)
        return points[-1][1] + (minute - points[-1][0]) * per_min

    xs = {sid: x0 + info[sid]['lane'] * lane_w for sid in st}
    paths = []
    for k in range(n_lanes):
        mine = [sid for sid in st if info[sid]['lane'] == k]
        if len(mine) > 1:
            paths.append({'d': f'M{xs[mine[0]]:g} {ys[mine[0]]:g} V{ys[mine[-1]]:g}', 'lane': k})
        elif mine:
            paths.append({'d': f'M{xs[mine[0]]:g} {ys[mine[0]] - 14:g} V{ys[mine[0]]:g}', 'lane': k})
    for a, z in b['edges']:
        if info[a]['lane'] != info[z]['lane']:
            paths.append({'d': _curve(xs[a], ys[a], xs[z], ys[z]), 'lane': info[a]['lane']})
    stations = []
    for sid in st:
        s = dict(info[sid], x=xs[sid], y=round(ys[sid], 1))
        if s['merge']:  # the wide station spans the lines that meet there
            here = {info[a]['lane'] for a, z in b['edges'] if z == sid} | {s['lane']}
            s['x0'], s['x1'] = x0 + min(here) * lane_w, x0 + max(here) * lane_w
            s['meets'] = sorted(here)
        if s['end'] > s['a_end']:
            s['stand'] = {'y0': round(y_at(s['a_end']), 1), 'y1': round(y_at(s['end']), 1)}
        stations.append(s)
    height = max([ys[st[-1]]] + [s['stand']['y1'] for s in stations if s.get('stand')]) + 30
    step = 30 if total > 150 else 15 if total > 70 else 10
    # Minute marks down the side, but none inside a shortened stretch
    ticks = [{'m': m, 'y': round(y_at(m), 1)} for m in range(0, total + 1, step)
             if not any(br['from'] < m < br['to'] for br in breaks)]
    return {'lanes': b['lanes'], 'width': x0 * 2 + (n_lanes - 1) * lane_w, 'height': round(height, 1),
            'paths': paths, 'stations': stations, 'breaks': breaks, 'ticks': ticks}
