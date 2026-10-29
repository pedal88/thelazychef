"""The river delta: the whole recipe as one drawing (docs/prototypes/stor-skjerm.html, skFit).

Rivers of work run from the first steps into the dish. This module decides the
drawing from the graph; the browser only places it (portrait or landscape),
scales it to fit and draws the arrows (static/js/delta.js).

- A prep step with no inputs and one consumer is folded into that step: its
  ingredients are drawn there, as a field when they are mixed in a bowl.
- A step with no ingredients of its own that follows the only step leading to it
  becomes an extra verb on that step ("cook the pasta → drain").
- The steps form a tree towards the final step. The heaviest branch runs through
  the middle, and the main line (most active time) is drawn larger.
- A result used in a second step gets a note there, not an arrow across the drawing.
- Numbers are the step numbers of the method list, so step 6 is the same step everywhere. The steps folded away
  are listed on their node ('folded'), for a page that shows every step.
"""
from services.measures import DEFAULT, degrees
from services.recipe_v2 import states
from services.recipe_v2.planner import steps_from_v2

HEAT = {'low': 1, 'medium_low': 2, 'medium': 2, 'medium_high': 3, 'high': 3}
# Verbs that say too little on their own; they always get their object ("cook the rice", not "cook")
GENERIC = {'cook', 'make', 'prepare', 'add', 'ha i', 'ha', 'kok', 'lag', 'tilbered', 'gjør'}
BOWLS = {'bowl', 'small_bowl', 'large_bowl'}
EARLY_MINUTES = 30  # a side branch that stands this long is started first


def _setup_like(s):
    return not s.get('uses') and (s.get('setup') or not s.get('after'))


def label(s, has_pics, near):
    """The verb when the pictures say the rest, else the short name (lower case, at most four words)."""
    verb = (s.get('verb') or '').strip().lower()
    short = (s.get('short') or '').strip()
    words = short.split()
    if verb and has_pics and verb not in near and verb not in GENERIC:
        return verb
    if len(words) <= 4:
        return short[:1].lower() + short[1:]
    return f"{verb or words[0].lower()} {words[-1]}"


def build(v2, order, lines, system=DEFAULT):
    """The delta for a v2 recipe, or None when it has no steps.

    order is the planned order of step ids (plan_v2()['order']). lines maps a line's local_id to what the
    drawing shows for it: {'name', 'img', 'amount', 'prep', 'cut'}. Temperatures are in the reader's measuring
    system (°C or °F, services/measures.py)."""
    by = {s['local_id']: s for s in v2.get('steps') or []}
    if not by:
        return None
    order = [sid for sid in order if sid in by]
    number = {sid: n for n, sid in enumerate(order, 1)}
    waits = {s.id: s.waits for s in steps_from_v2(v2)}
    graph = [sid for sid in order if not _setup_like(by[sid])]
    ids = set(graph)
    preds = {sid: [a for a in by[sid].get('after') or [] if a in ids] for sid in graph}
    cons = {sid: [] for sid in graph}
    for sid in graph:
        for a in preds[sid]:
            cons[a].append(sid)
    finals = [sid for sid in graph if not cons[sid]]
    if not finals:
        return None
    fin = next((sid for sid in reversed(finals) if by[sid]['phase'] == 'serve'), finals[-1])

    def prep_source(sid):
        return by[sid]['phase'] == 'prep' and not preds[sid] and len(cons[sid]) == 1

    acc = {}

    def active_to(sid):  # most active minutes on any path into this step
        if sid not in acc:
            acc[sid] = (by[sid].get('active_minutes') or 0) + max([active_to(a) for a in preds[sid]], default=0)
        return acc[sid]

    main, cur = set(), fin
    while cur:
        main.add(cur)
        ps = [a for a in preds[cur] if not prep_source(a)]
        cur = max(ps, key=active_to) if ps else None

    # Fold prep sources into their consumer
    folded, hidden = {}, set()
    for sid in graph:
        if prep_source(sid) and sid != fin:
            folded.setdefault(cons[sid][0], []).append(sid)
            hidden.add(sid)
    steps = [sid for sid in graph if sid not in hidden]
    shown = set(steps)

    def pr(sid):
        return [a for a in preds[sid] if a in shown]

    def co(sid):
        return [t for t in cons[sid] if t in shown]

    def items(sid):
        return [u for f in folded.get(sid, []) for u in by[f].get('uses') or []] + list(by[sid].get('uses') or [])

    # Merge a step with no ingredients into the only step before it, when that step leads nowhere else
    rep, tail = {}, {}
    for sid in steps:
        rep[sid] = sid
        ps = pr(sid)
        if not items(sid) and len(ps) == 1 and len(co(ps[0])) == 1:
            head = rep[ps[0]]
            rep[sid] = head
            tail.setdefault(head, []).append(sid)
    nodes = [sid for sid in steps if rep[sid] == sid]
    root = rep[fin]

    kids, parent = {sid: [] for sid in nodes}, {}
    for t in steps:
        for a in pr(t):
            ra, rt = rep[a], rep[t]
            if ra != rt and ra not in parent:
                parent[ra] = rt
                kids[rt].append(ra)

    edges, seen, also = [], set(), {}
    for sid in steps:
        for t in co(sid):
            a, b = rep[sid], rep[t]
            if a == b or (a, b) in seen:
                continue
            seen.add((a, b))
            if parent.get(a) == b:
                edges.append([a, b])
            else:
                also.setdefault(b, []).append(sid)

    def chain(sid):
        return [sid] + tail.get(sid, [])

    def is_main(sid):
        return any(x in main for x in chain(sid))

    weights = {}

    def weight(sid):
        if sid not in weights:
            weights[sid] = sum(by[x].get('active_minutes') or 0 for x in chain(sid)) + sum(weight(k) for k in kids[sid])
        return weights[sid]

    depth = {}

    def set_depth(sid, d):
        depth[sid] = d
        for k in kids[sid]:
            set_depth(k, d + 1)
    set_depth(root, 0)

    def placed(sid):  # the heaviest branch in the middle, the others alternating around it
        ks = sorted(kids[sid], key=lambda k: (1e6 if is_main(k) else 0) + weight(k))
        heavy, out = (ks.pop() if ks else None), []
        for i, k in enumerate(ks):
            if i % 2:
                out.append(k)
            else:
                out.insert(0, k)
        if heavy:
            out.insert((len(out) + 1) // 2, heavy)
        return out

    leaf_count = {}

    def leaves(sid):
        if sid not in leaf_count:
            leaf_count[sid] = sum(leaves(k) for k in kids[sid]) if kids[sid] else 1
        return leaf_count[sid]

    span = {}

    def place(sid, start):
        span[sid] = [start, start + leaves(sid)]
        c = start
        for k in placed(sid):
            place(k, c)
            c += leaves(k)
    place(root, 0)

    def pic(u):
        line = lines.get(u) or {'name': u}
        return {**line, 'mark': states.mark(line.get('cut'))}

    def is_bowl(f):
        s = by[f]
        return len(s.get('uses') or []) > 1 and bool(BOWLS & set(s.get('equipment') or []))

    out, listed = [], set()  # a setting up two steps wait for is listed on the first
    for sid in nodes:
        if sid not in span:
            continue  # not connected to the dish
        steps_here = chain(sid)
        own = items(sid)
        near = [(by[x].get('verb') or '').lower() for x in pr(sid) + co(steps_here[-1])]
        segs = []
        for k, x in enumerate(steps_here):
            s = by[x]
            segs.append({'id': x, 'no': number[x], 'short': s.get('short') or '',
                         'label': label(s, k == 0 and bool(own), near if k == 0 else []),
                         'heat': HEAT.get(s.get('mode') or '', 0), 'temp': degrees(s.get('temp_c'), system),
                         'wait': s.get('passive_minutes') if (s.get('passive_minutes') or 0) >= 5 else None})
        notes, setup = [], []
        for x in steps_here:
            for w in waits.get(x) or []:
                if w in by:
                    notes.append(label(by[w], False, []) + (f" {degrees(by[w]['temp_c'], system)}°" if by[w].get('temp_c') else ''))
                    setup.append(w)
        # The steps the drawing folds away (a prep step drawn as its ingredients, a setting up the step waits for),
        # for a page that shows every step: number and label, in the order of the method
        hidden_here = sorted((set(folded.get(sid, [])) | set(setup)) - listed, key=lambda x: number[x])
        listed.update(hidden_here)
        bowls = [[pic(u) for u in by[f].get('uses') or []] for f in folded.get(sid, []) if is_bowl(f)]
        loose = [u for f in folded.get(sid, []) if not is_bowl(f) for u in by[f].get('uses') or []] + list(by[sid].get('uses') or [])
        out.append({
            'id': sid, 'phase': by[sid]['phase'], 'main': is_main(sid), 'depth': depth[sid], 'span': span[sid],
            'chain': segs, 'notes': list(dict.fromkeys(notes)), 'bowls': bowls, 'pics': [pic(u) for u in loose],
            'early': not is_main(sid) and any((by[x].get('passive_minutes') or 0) >= EARLY_MINUTES for x in steps_here),
            'also': [{'no': number[x], 'short': by[x].get('short') or ''} for x in also.get(sid, [])],
            'folded': [{'id': x, 'no': number[x], 'short': by[x].get('short') or '',
                        'label': label(by[x], False, []) + (f" {degrees(by[x]['temp_c'], system)}°" if by[x].get('temp_c') else '')} for x in hidden_here],
        })
    return {'nodes': out, 'edges': edges, 'max_depth': max(depth.values()), 'leaves': leaves(root)}
