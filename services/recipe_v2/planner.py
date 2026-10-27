"""The planner: when each step is done, from the recipe graph.

A port of schedule() in docs/prototypes/fem-retter.html and the v2 adapter in
fem-retter-pilot.html. tests/test_recipe_v2_planner.py checks that it gives the
same plans as the prototype for 25 recipes (scripts/make_planner_golden.mjs).

Times are minutes from the start. The plan is built backwards from serving:
each step is placed as late as its successors allow, the cook works on one
active step at a time, and exclusive equipment (the oven) holds one thing, or as many as its capacity (an air
fryer with two drawers holds two).
Three strategies, decided by the user (RECIPE_VISUALIZATIONS.md 9.12):

    calm  prep before cooking, but prep that can wait is done while something stands (default)
    prep  everything that needs no heat is done before the first cook step
    jit   every step as late as possible: shortest, busiest

The capacity comes from the equipment catalog (data/constraints/equipment.json, "capacity", 1 when left out). A
kitchen, {equipment id: capacity}, overrides it for one plan: the user's own kitchen (one drawer, or two ovens),
when there is such a setting.

Waiting for equipment is not stored. A step waits for the setup step on the
same cookware (preheat the oven), and with several, for the one at the same
temperature (docs/RECIPE_MODEL_V2.md, section 3).
"""
import json
import os
from dataclasses import dataclass, field
from functools import lru_cache

MODES = ('calm', 'prep', 'jit')
BUF = 2  # minutes of slack around prep fitted into a free period


@lru_cache(maxsize=1)
def _equipment():
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                        'data', 'constraints', 'equipment.json')
    with open(path, encoding='utf-8') as f:
        return {e['id']: e for e in json.load(f)['equipment']}


@dataclass
class Step:
    id: str
    phase: str
    after: list
    uses: list
    active: int
    passive: int
    hold: int | None = None
    setup: bool = False
    eq: str | None = None  # the cookware, when the step happens on or in one
    temp: int | None = None
    excl: bool = False  # the cookware holds one thing at a time (oven)
    cap: int = 1  # or this many at a time (an air fryer with two drawers)
    waits: list = field(default_factory=list)

    @property
    def dur(self):
        return self.active + self.passive


def steps_from_v2(v2, kitchen=None):
    """The recipe's steps as planner steps, with the waits for setup steps derived. kitchen: {equipment id: capacity}
    over the catalog's."""
    raw = v2.get('steps') or []
    cat = _equipment()
    kitchen = kitchen or {}

    def prep_of(s):  # gets equipment ready: setup, or a step with no ingredients and no inputs ("line the tin")
        return s.get('setup') or (not s.get('uses') and not s.get('after'))

    def setup_for(s):
        q = (s.get('equipment') or [None])[0]
        if not q:
            return None
        cands = [t for t in raw if t is not s and prep_of(t) and (t.get('equipment') or [None])[0] == q]
        same_temp = next((t for t in cands if t.get('temp_c') and t.get('temp_c') == s.get('temp_c')), None)
        pick = same_temp or (cands[0] if cands else None)
        return pick['local_id'] if pick else None

    steps = []
    for s in raw:
        q = (s.get('equipment') or [None])[0]
        info = cat.get(q) or {}
        pot = bool(q and (info.get('role') == 'koke' or s.get('temp_c') or s.get('mode')))
        step = Step(id=s['local_id'], phase=s['phase'], after=list(s.get('after') or []), uses=list(s.get('uses') or []),
                    active=s.get('active_minutes') or 0, passive=s.get('passive_minutes') or 0,
                    hold=s.get('holds_minutes'), setup=bool(s.get('setup')), eq=q if pot else None,
                    temp=s.get('temp_c'), excl=bool(pot and info.get('exclusive') and not s.get('setup')),
                    cap=max(1, int(kitchen.get(q, info.get('capacity', 1)))))
        w = pot and not prep_of(s) and setup_for(s)
        if w and w not in step.after:
            step.waits = [w]
        steps.append(step)
    return steps


def _fit(busy, eqb, r, s):
    """Move a step to the first free place: the cook does one active step at a time, and exclusive cookware holds one thing."""
    moved = True
    while moved:
        moved = False
        if s.active:
            a = r + s.passive
            b = a + s.active
            for x, y in busy:
                if a < y and x < b:
                    r = y - s.passive
                    moved = True
                    break
        if not moved and s.excl and s.cap == 1:
            a, b = r, r + s.active + s.passive
            for x, y in eqb.get(s.eq, []):
                if a < y and x < b:
                    r = y
                    moved = True
                    break
        elif not moved and s.excl:  # room for cap things at once: move only where it would be one too many
            a, b = r, r + s.active + s.passive
            over = [(x, y) for x, y in eqb.get(s.eq, []) if a < y and x < b]
            if _peak(over, a, b) >= s.cap:
                r = min(y for _, y in over)
                moved = True
    return r


def _peak(intervals, a, b):
    """The most of the intervals that are under way at once between a and b."""
    edges = sorted([(max(x, a), 1) for x, _ in intervals] + [(min(y, b), -1) for _, y in intervals], key=lambda e: (e[0], e[1]))
    n = top = 0
    for _, d in edges:
        n += d
        top = max(top, n)
    return top


def schedule(steps, mode='calm'):
    """Plan the steps. Returns a dict with plan (start, a_end, end, use, during per step), T, order and more.

    Internally the plan runs backwards: r is minutes before serving that a step ends, e when it starts."""
    if mode not in MODES:
        raise ValueError(f'Unknown plan {mode!r}')
    by = {s.id: s for s in steps}

    def pre(s):
        return s.after + s.waits

    succ = {s.id: [] for s in steps}
    for s in steps:
        for a in pre(s):
            succ[a].append(s.id)

    rr = {}

    def rank(s):  # longest path from the start through this step
        if s.id not in rr:
            rr[s.id] = s.dur + max([0] + [rank(by[a]) for a in pre(s)])
        return rr[s.id]

    for s in steps:
        rank(s)
    ah = {}

    def ahead(s):  # prep that only depends on prep: can be done before cooking
        if s.id not in ah:
            ah[s.id] = s.phase == 'prep' and all(ahead(by[a]) for a in pre(s))
        return ah[s.id]

    for s in steps:
        ahead(s)

    R, busy, eqb = {}, [], {}

    def in_window(s, need, hi):
        """calm: the earliest free period inside the cooking (no active steps) that fits the step with slack."""
        if not s.active:
            return None
        iv = sorted((iv for iv in busy if iv[0] < hi), key=lambda iv: iv[0])
        gaps, cur = [], 0
        for x, y in iv:
            if x > cur:
                gaps.append((cur, x))
            cur = max(cur, y)
        if cur < hi:
            gaps.append((cur, hi))
        best = None
        for x, y in gaps:
            if y - x < s.active + 2 * BUF:
                continue
            r0 = max(need, x + BUF - s.passive)
            if r0 + s.passive + s.active <= y - BUF and (s.hold is None or r0 - need <= s.hold) and (best is None or r0 < best):
                best = r0
        return best

    def run(ids, floor, win):
        left = list(ids)
        while left:
            best = None
            for sid in left:
                if not all(x in R for x in succ[sid]):
                    continue
                s = by[sid]
                # Steps done ahead go before the cooking starts (floor), never earlier than their result can wait (hold).
                need = max([0] + [R[x][1] for x in succ[sid]])
                want = floor - s.passive
                if s.hold is not None:
                    want = min(want, need + s.hold)
                r0 = _fit(busy, eqb, max(need, want), s)
                if s.hold is not None and r0 - need > s.hold:
                    r0 = _fit(busy, eqb, need, s)
                if win:
                    w = in_window(s, need, win)
                    if w is not None and w < r0:
                        r0 = w
                if best is None or r0 < best[1] or (r0 == best[1] and rr[sid] > rr[best[0]]):
                    best = (sid, r0)
            if best is None:
                raise ValueError('The steps form a cycle')
            s = by[best[0]]
            R[s.id] = (best[1], best[1] + s.dur)
            if s.active:
                busy.append((best[1] + s.passive, best[1] + s.passive + s.active))
            if s.excl:
                eqb.setdefault(s.eq, []).append((best[1], best[1] + s.dur))
            left.remove(s.id)

    late = [s.id for s in steps if not ah[s.id]]
    early = [s.id for s in steps if ah[s.id]]
    run(late, 0, 0)
    cs = max([0] + [R[i][1] for i in late if not by[i].setup])
    run(early, 0 if mode == 'jit' else cs, cs if mode == 'calm' else 0)

    T = max(e for _, e in R.values())
    plan = {}
    for s in steps:
        st = T - R[s.id][1]
        plan[s.id] = {'start': st, 'a_end': st + s.active, 'end': st + s.dur}
    # A step that only stands (no active time) starts as soon as its inputs are ready.
    for s in steps:
        if s.active or not s.after:
            continue
        p = plan[s.id]
        ready = max(plan[a]['end'] for a in s.after)
        if ready < p['start']:
            p['start'] = p['a_end'] = ready
    for s in steps:
        plan[s.id]['use'] = min(plan[x]['start'] for x in succ[s.id]) if succ[s.id] else plan[s.id]['end']
    order = sorted(steps, key=lambda s: (plan[s.id]['start'], plan[s.id]['a_end']))
    act = sorted((plan[s.id]['start'], plan[s.id]['a_end']) for s in steps if s.active)
    me = []
    for x, y in act:
        if me and x <= me[-1][1]:
            me[-1][1] = max(me[-1][1], y)
        else:
            me.append([x, y])

    def first(ph):
        return min([T] + [plan[s.id]['start'] for s in steps if s.phase == ph and not s.setup])

    # during: the standing cook step a later prep step is done in ("mens lasagnen står").
    c0 = first('cook')
    for s in steps:
        p = plan[s.id]
        if s.phase != 'prep' or p['start'] < c0:
            continue
        cands = [w for w in steps if w.phase == 'cook' and not w.setup and w.passive >= 8
                 and plan[w.id]['a_end'] <= p['start'] < plan[w.id]['end']]
        cands.sort(key=lambda w: -w.passive)
        if cands:
            p['during'] = cands[0].id
    over = [s.id for s in steps if s.hold is not None and plan[s.id]['use'] - plan[s.id]['end'] > s.hold]
    return {'plan': plan, 'T': T, 'order': [s.id for s in order], 'me': me, 'ahead': sorted(k for k, v in ah.items() if v),
            'over': over, 'cook_start': first('cook'), 'serve_start': first('serve'), 'A': sum(s.active for s in steps)}


def plan_v2(v2, mode='calm', kitchen=None):
    """Plan a recipe in v2 JSON (services/recipe_v2/store.to_v2). kitchen: {equipment id: capacity}, the user's own
    over the catalog's (an air fryer with one drawer: {'airfryer': 1})."""
    return schedule(steps_from_v2(v2, kitchen), mode)
