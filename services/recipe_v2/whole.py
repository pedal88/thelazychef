"""The whole dish beside cooking mode: the timeline and the metro map (RECIPE_VISUALIZATIONS.md 9.15).

Ported from the large-screen prototype (vTimelineW and vMetroV in docs/prototypes/stor-skjerm.html).
Both are drawn from the plan, so they show the same order and minutes as the method list and the cards;
the river delta (delta.py) is the third view. Step numbers are the method list's numbers everywhere.
The page marks the step you are on (static/js/cook.js).
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
            free.append({'left': pct(y), 'width': pct(gap), 'minutes': gap, 'label': gap / total > 0.09})
    step = 30 if total > 150 else 15 if total > 70 else 10
    return {
        'total': total, 'rows': rows, 'busy': busy, 'free': free,
        'ticks': [{'left': pct(t), 'label': t} for t in range(0, total + 1, step)],
        'phases': [{'x': round(x / total, 4), 'label': label, 'right': x / total > 0.9}
                   for x, label in ((sch.get('cook_start'), 'cook'), (sch.get('serve_start'), 'serve')) if x and 0 < x < total],
    }


def metro(v2, sch, comps):
    """The metro map, top to bottom: each part of the dish is a line, and the stations come in the order you
    start them. Returns the SVG geometry; the template draws it."""
    by = {s['local_id']: s for s in v2.get('steps') or []}
    order = [sid for sid in sch['order'] if sid in by]
    number = {sid: n for n, sid in enumerate(order, 1)}
    stations = [sid for sid in order if not _header(by[sid])]
    if not stations:
        return None
    lanes = list(dict.fromkeys(by[sid]['component_id'] for sid in stations))
    final = next((sid for sid in stations if not any(sid in (by[t].get('after') or []) for t in stations)), stations[-1])
    row_h, top, lane_w, x0 = 38, 20, 24, 48
    row = {sid: k for k, sid in enumerate(stations)}

    def pos(sid):
        return x0 + lanes.index(by[sid]['component_id']) * lane_w, top + row[sid] * row_h

    paths = []
    for lane in lanes:
        first = next(sid for sid in stations if by[sid]['component_id'] == lane)
        x, y = pos(first)
        paths.append({'d': f'M{x} {max(4, y - row_h * 0.45):g} V{y}', 'lane': lanes.index(lane)})
    for sid in stations:
        bx, by_ = pos(sid)
        for a in by[sid].get('after') or []:
            if a not in row:
                continue
            ax, ay = pos(a)
            dy = min(row_h * 0.7, (by_ - ay) / 2)
            d = f'M{ax} {ay} V{by_}' if ax == bx else \
                f'M{ax} {ay} V{by_ - 2 * dy:g} C{ax} {by_ - dy:g} {bx} {by_ - dy:g} {bx} {by_}'
            paths.append({'d': d, 'lane': lanes.index(by[a]['component_id'])})
    text_x = x0 + (len(lanes) - 1) * lane_w + 22
    return {
        'width': 420, 'height': top + (len(stations) - 1) * row_h + 22, 'row_h': row_h, 'text_x': text_x, 'min_x': x0 - 22,
        'lanes': [{'name': comps.get(c, c), 'n': k % 4} for k, c in enumerate(lanes)],
        'paths': paths,
        'stations': [{'id': sid, 'no': number[sid], 'short': by[sid]['short'], 'phase': by[sid]['phase'],
                      'start': sch['plan'][sid]['start'], 'final': sid == final,
                      'x': pos(sid)[0], 'y': pos(sid)[1]} for sid in stations],
    }


# Metro map trials (25.10.2026; routes/_shared.py VIEW_TRIALS): three redrawings of the same map, to compare.
# All share the stations (the steps that take or make something, in planned order), the lanes (one per part of
# the dish) and the links between them; they differ in how they place them. Labels are HTML beside the drawing,
# so the text keeps its size on a phone instead of shrinking with an SVG.

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
    total = max(1, sch['T'])

    def minutes(s):
        active, standing = s.get('active_minutes') or 0, s.get('passive_minutes') or 0
        return f"{active} min" + (f" + {standing}" if standing else '') if active else (f"{standing} min" if standing else '')

    info = {sid: {'id': sid, 'no': number[sid], 'short': by[sid]['short'], 'phase': by[sid]['phase'], 'lane': lane_of[sid],
                  'start': sch['plan'][sid]['start'], 'a_end': sch['plan'][sid]['a_end'], 'end': sch['plan'][sid]['end'],
                  'final': sid == final, 'time': minutes(by[sid]),
                  # where two parts of the dish meet: a step that takes something from another line
                  'merge': any(lane_of[a] != lane_of[sid] for a, b in edges if b == sid)} for sid in stations}
    return {'stations': stations, 'lanes': [{'name': comps.get(c, c), 'n': k % 4} for k, c in enumerate(lanes)],
            'edges': edges, 'info': info, 'total': total}


def _curve(ax, ay, bx, by_, vertical=True, bend=0.6):
    if vertical:
        if ax == bx:
            return f'M{ax:g} {ay:g} V{by_:g}'
        dy = (by_ - ay) * bend
        return f'M{ax:g} {ay:g} C{ax:g} {ay + dy:g} {bx:g} {by_ - dy:g} {bx:g} {by_:g}'
    if ay == by_:
        return f'M{ax:g} {ay:g} H{bx:g}'
    dx = (bx - ax) * bend
    return f'M{ax:g} {ay:g} C{ax + dx:g} {ay:g} {bx - dx:g} {by_:g} {bx:g} {by_:g}'


def metro_trials(v2, sch, comps):
    """{'m1': ..., 'm2': ..., 'm3': ...}: the geometry of the three trial maps, or None without stations.

    m1 Transit: the map as now, top to bottom in the order you start the steps, drawn as a real transit map: thick
       lines in colours of their own, white stations, a wide station where two parts of the dish meet, the end
       station large; time and phase beside each name.
    m2 Timed: the same, with the distance down the map following the minutes, so waiting shows as long stretches,
       standing time as a dashed stretch, and a line for now.
    m3 Lines: left to right, one horizontal line per part of the dish, joining the main line where it is used."""
    b = _metro_base(v2, sch, comps)
    if not b:
        return None
    st, info, n_lanes = b['stations'], b['info'], len(b['lanes'])

    def vertical(ys, lane_w=22, x0=20):
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
        width = x0 * 2 + (n_lanes - 1) * lane_w
        stations = []
        for sid in st:
            s = dict(info[sid], x=xs[sid], y=ys[sid])
            if s['merge']:  # the wide station spans the lines that meet there
                lanes_here = {info[a]['lane'] for a, z in b['edges'] if z == sid} | {s['lane']}
                s['x0'], s['x1'] = x0 + min(lanes_here) * lane_w, x0 + max(lanes_here) * lane_w
            stations.append(s)
        return {'width': width, 'paths': paths, 'stations': stations}

    # m1: one row per station
    row, top = 56, 30
    ys = {sid: top + k * row for k, sid in enumerate(st)}
    m1 = dict(vertical(ys), height=ys[st[-1]] + 30, row=row)

    # m2: down the page by the minute, never closer than a label needs
    per_min = max(3.0, min(9.0, 720 / b['total']))
    ys2, last = {}, None
    for sid in st:
        y = top + info[sid]['start'] * per_min
        if last is not None and y < last + 34:
            y = last + 34
        ys2[sid] = last = y
    m2 = dict(vertical(ys2), height=last + 40, row=34)
    # standing time as a dashed stretch beside the station, from when your work ends to when it is ready
    def y_at(minute):  # the minute on the stretched axis: between the stations around it
        pts = sorted({(info[sid]['start'], ys2[sid]) for sid in st})
        if minute <= pts[0][0]:
            return top + minute * per_min
        for (m0, y0), (m1_, y1) in zip(pts, pts[1:]):
            if m0 <= minute <= m1_:
                return y0 if m1_ == m0 else y0 + (y1 - y0) * (minute - m0) / (m1_ - m0)
        return pts[-1][1] + (minute - pts[-1][0]) * per_min
    for s in m2['stations']:
        if s['end'] > s['a_end']:
            s['stand'] = {'y0': round(y_at(s['a_end']), 1), 'y1': round(y_at(s['end']), 1)}
    m2['height'] = max(m2['height'], max((s['stand']['y1'] for s in m2['stations'] if s.get('stand')), default=0) + 30)
    step_tick = 30 if b['total'] > 150 else 15 if b['total'] > 70 else 10
    m2['ticks'] = [{'m': m, 'y': round(y_at(m), 1)} for m in range(0, b['total'] + 1, step_tick)]

    # m3: left to right, a column per station, a row per part of the dish (the part of the last station on top)
    col, lane_h, left, top3 = 104, 112, 24, 30
    xs3 = {sid: left + col / 2 + k * col for k, sid in enumerate(st)}
    order_lanes = [info[st[-1]]['lane']] + [k for k in range(n_lanes) if k != info[st[-1]]['lane']]
    ys3_lane = {k: top3 + order_lanes.index(k) * lane_h for k in range(n_lanes)}
    paths3 = []
    for k in range(n_lanes):
        mine = [sid for sid in st if info[sid]['lane'] == k]
        if mine:
            paths3.append({'d': f'M{xs3[mine[0]] - col * 0.4:g} {ys3_lane[k]:g} H{xs3[mine[-1]]:g}', 'lane': k})
    for a, z in b['edges']:
        if info[a]['lane'] != info[z]['lane']:
            paths3.append({'d': _curve(xs3[a], ys3_lane[info[a]['lane']], xs3[z], ys3_lane[info[z]['lane']], vertical=False, bend=0.55),
                           'lane': info[a]['lane']})
    m3 = {'width': left * 2 + len(st) * col, 'height': top3 + (n_lanes - 1) * lane_h + 64, 'col': col, 'paths': paths3,
          'lane_rows': [{'n': b['lanes'][k]['n'], 'name': b['lanes'][k]['name'], 'y': ys3_lane[k],
                         'x': xs3[next(sid for sid in st if info[sid]['lane'] == k)] - col * 0.4} for k in range(n_lanes)],
          # the joining curves show where the parts meet, so no wide station here
          'stations': [dict(info[sid], x=xs3[sid], y=ys3_lane[info[sid]['lane']], merge=False) for sid in st]}
    return {'lanes': b['lanes'], 'm1': m1, 'm2': m2, 'm3': m3}
