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
