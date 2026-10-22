"""Prep (Gjør klart): what to set out before the cooking starts, derived from the graph.

The rules are in RECIPE_VISUALIZATIONS.md 9.10 and 9.15; the AI does not make mise elements.

A mise element is what stands ready when prep is done and goes in at the same time:
- the lines that go straight into a step are one element, used in that step;
- the lines worked in prep steps done ahead (cut, mixed) are one element, used where the result of that
  prep goes in. A step that stands on the clock (rising, marinating) ends the prep: it is a step of its own;
- lines to taste have no amount to set out: they stand on the counter.

An element is a bowl when there is a reason to fill one, otherwise its lines are taken out and
measured when they are used:
1. prep: a prep step works on it, or a line is cut or brought to a state (softened, melted, juiced);
2. mix: three or more small amounts (tsp, tbsp, pinch, at most 30 g) go in together, like a spice mix;
3. rush: two or more lines go into a step on medium heat or more with at most 2 active minutes.
Staples alone (the pantry tier "staple": salt, pepper, oil, water, sugar, flour) stand on the counter. Only bowls are numbered, in the
order they are used. Prep that the plan puts in a waiting time comes later, "while the lasagne stands".
"""
import re

SMALL_UNITS = {'tsp', 'tbsp', 'pinch', 'dash', 'drop'}
HOT = {'medium', 'medium_high', 'high'}
STAPLES = {'salt', 'sea salt', 'flaky salt', 'pepper', 'black pepper', 'salt and pepper', 'water', 'olive oil',
           'vegetable oil', 'neutral oil', 'rapeseed oil', 'canola oil', 'sunflower oil',
           'havsalt', 'flaksalt', 'sort pepper', 'salt og pepper', 'vann', 'olivenolje', 'nøytral olje', 'rapsolje',
           'solsikkeolje'}
# A state the cook brings a line to before it goes in. "Chopped tomatoes" is a product, not a state, and has no cut.
WORKED = re.compile(r'soft|room temp|melted|beaten|whisked|juice|zest|squeezed|lukewarm|toasted|'
                    r'myk|romtemp|smeltet|pisket|saft|skall|presset|lunken|ristet', re.I)
AND = {'nb': 'og'}
STANDS = 10  # minutes on the clock that make a prep step a step of its own


def staple(line):
    """Salt, pepper, oil and the like. The pantry decides (tier 'staple'); a line not in the pantry goes by its name."""
    if 'pantry_tier' in line:
        return line['pantry_tier'] == 'staple'
    return (line.get('name') or '').strip().lower() in STAPLES or (line.get('pantry_name') or '').lower() in STAPLES


def worked(line):
    return bool(line.get('cut')) or bool(WORKED.search(line.get('prep_style') or ''))


def small(line):
    return line.get('unit') in SMALL_UNITS or (line.get('unit') == 'g' and (line.get('amount') or 0) <= 30)


def joined(names, language):
    """"Onion, carrot and garlic" in the recipe's language."""
    names = [n[:1].upper() + n[1:] if k == 0 else n for k, n in enumerate(names)]
    if len(names) > 3:
        names = names[:2] + [f'{len(names) - 2} more' if language != 'nb' else f'{len(names) - 2} til']
    word = AND.get(language, 'and')
    return names[0] if len(names) == 1 else f"{', '.join(names[:-1])} {word} {names[-1]}"


def build(v2, sch, language=None):
    """The Prep page for a planned v2 recipe: bowls, things to take out, the counter and later bowls.

    sch is plan_v2(v2, plan). Steps are referred to by their number in the method list (the planned order)."""
    by = {s['local_id']: s for s in v2.get('steps') or []}
    if not by:
        return None
    lines = {i['local_id']: i for i in v2['ingredients']}
    order = [sid for sid in sch['order'] if sid in by]
    number = {sid: n for n, sid in enumerate(order, 1)}
    plan, ahead = sch['plan'], set(sch.get('ahead') or [])
    cons = {sid: [] for sid in order}
    for sid in order:
        for a in by[sid].get('after') or []:
            if a in cons:
                cons[a].append(sid)

    def exit_of(sid):  # the last prep step done ahead before the result goes into the cooking
        nxt = cons[sid]
        if len(nxt) == 1 and nxt[0] in ahead and (by[nxt[0]].get('passive_minutes') or 0) < STANDS:
            return exit_of(nxt[0])
        return sid

    def in_prep(sid):  # prep done ahead that is not a step on the clock of its own
        return sid in ahead and (by[sid].get('passive_minutes') or 0) < STANDS

    # Group the lines into elements, keyed by the step whose result (or which) they stand ready for
    elements = {}
    for sid in order:
        s = by[sid]
        if not s.get('uses'):
            continue
        key = exit_of(sid) if in_prep(sid) else sid
        e = elements.setdefault(key, {'key': key, 'lines': [], 'prep': []})
        e['lines'] += [lines[u] for u in s['uses'] if u in lines]
        if in_prep(sid):
            e['prep'].append(sid)

    out = {'bowls': [], 'fetch': [], 'bench': [], 'later': []}
    later = {}
    seen_bench = set()
    for e in sorted(elements.values(), key=lambda e: (plan[used_of(e, cons)]['start'], number[used_of(e, cons)])):
        used = used_of(e, cons)
        st = by[used]
        vis = [i for i in e['lines'] if i.get('amount') is not None]
        reasons = []
        if e['prep'] or any(worked(i) for i in vis):
            reasons.append('prep')
        if sum(1 for i in vis if small(i)) >= 3:
            reasons.append('mix')
        if st['phase'] == 'cook' and not st.get('setup') and st.get('mode') in HOT and (st.get('active_minutes') or 0) <= 2 and len(vis) >= 2:
            reasons.append('rush')
        if not vis or (all(staple(i) for i in vis) and not e['prep']):
            kind = 'bench'
        else:
            kind = 'bowl' if reasons else 'fetch'
        target = {'id': used, 'no': number[used], 'short': st['short'], 'phase': st['phase'], 'start': plan[used]['start']}
        # The counter: staples on their own, and everything to taste
        for i in e['lines'] if kind == 'bench' else [i for i in e['lines'] if i.get('amount') is None]:
            k = (i['name'].lower(), i.get('amount'), used)
            if k not in seen_bench:
                seen_bench.add(k)
                out['bench'].append({'key': f"c:{i['local_id']}", 'line': i, 'used': target})
        if kind == 'bench':
            continue
        while_id = next((plan[p].get('during') for p in e['prep'] if plan[p].get('during')), None)
        dest = later.setdefault(while_id, {'while': by[while_id]['short'], 'bowls': [], 'fetch': []}) if while_id else out
        if kind == 'bowl':
            name = by[e['key']]['short'] if e['prep'] else joined([i['name'] for i in vis], language)
            dest['bowls'].append({'key': f"b:{e['key']}", 'name': name, 'named_by_step': bool(e['prep']), 'lines': vis, 'used': target,
                                  # the prep steps besides the one the bowl is named after
                                  'prep': [by[p]['short'] for p in sorted(e['prep'], key=number.get) if p != e['key']],
                                  'why': reasons[0]})
        else:
            dest['fetch'] += [{'key': f"f:{i['local_id']}", 'line': i, 'used': target} for i in vis]
    out['later'] = list(later.values())
    # The prep steps done here, which cooking mode can skip
    out['done_here'] = sorted({p for e in elements.values() for p in e['prep']}, key=number.get)
    for n, b in enumerate(out['bowls'] + [b for g in out['later'] for b in g['bowls']], 1):
        b['no'] = n
    # Jobs before anything else: steps with no ingredients, no inputs and no cookware ("take the butter out")
    out['tasks'] = [{'key': f't:{sid}', 'short': by[sid]['short'], 'text': by[sid].get('text') or ''}
                    for sid in order if not by[sid].get('uses') and not by[sid].get('after') and not by[sid].get('equipment')]
    return out


def used_of(e, cons):
    """The step an element goes into: the step itself, or where the result of its prep goes in."""
    if not e['prep']:
        return e['key']
    nxt = cons[e['key']]
    return nxt[0] if nxt else e['key']
