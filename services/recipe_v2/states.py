"""The state catalog (data/constraints/states.json): what is done to an ingredient before it goes in.

state is an id, grade how fine or thin, and the app writes them in words. fill() gives a v2 recipe made before the
catalog (26.10.2026) its states: from prep_style where it says one ("finhakket" -> chop + fine, the rest stays as
the note), else from the method of the prep step that changes the line ("Skyll risen" -> rinse). A cut, grated or
pressed state read from the note alone, on a line no prep step works on, is how the product is sold ("hermetiske
tomater, hakkede") and stays a note. It never touches the steps, so a converted recipe keeps its step numbers.
"""
import json
import os
import re
from functools import lru_cache

PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data', 'constraints', 'states.json')

# Words in a synonym that say the grade ("finhakket", "roughly chopped", "tynne skiver", "stivpisket")
# The groups a product can be bought in ("hakkede tomater", "revet ost"): read from a note only on a line a prep step works on
SOLD_SO = {'cut', 'grate', 'press'}
GRADE_WORDS = (('fine', r'\bfin|finely|\bfine\b'), ('coarse', r'\bgrov|coarse|roughly'), ('thin', r'\btynn|thin'),
               ('thick', r'\btykk|thick'), ('stiff', r'\bstiv|stiff'), ('soft', r'\bmyke? topp|soft peak'),
               ('small', r'\bsmå\b|\bsmall\b'), ('large', r'\bstore\b|\blarge\b'))


@lru_cache(maxsize=1)
def catalog():
    with open(PATH, encoding='utf-8') as f:
        return json.load(f)


def by_id():
    return {s['id']: s for s in catalog()['states']}


def state_of_method(method):
    return next((s['id'] for s in catalog()['states'] if method in s['methods']), None)


def word(state, grade=None, lang='en'):
    """The state in words: "finely chopped", "fint hakket"; '' for no state."""
    s = by_id().get(state)
    if not s:
        return ''
    lang = 'nb' if lang == 'nb' else 'en'
    g = next((x for x in catalog()['grades'] if x['id'] == grade), None) if grade in s['grades'] else None
    if not g:
        return s[lang]
    return f"{s[lang]} ({g[lang]})" if grade in ('soft', 'stiff', 'small', 'large') else f"{g[lang]} {s[lang]}"


def from_text(text):
    """The state and grade a note says, and what is left of it: ("chop", "fine", "") for "finhakket",
    ("slice", "thin", "optional") for "thinly sliced, optional", (None, None, text) when it says none."""
    note = (text or '').strip()
    if not note:
        return None, None, ''
    low = note.lower()
    found = None  # the longest synonym that occurs, so "finely chopped" wins over "chopped"
    for s in catalog()['states']:
        for w in s['synonyms']['en'] + s['synonyms']['nb']:
            m = re.search(rf'(?<!\w){re.escape(w)}(?!\w)', low)
            if m and (not found or len(w) > len(found[1])):
                found = (s, w, m)
    if not found:
        return None, None, note
    s, w, m = found
    # The grade from the synonym itself, or from a word just before it ("very thinly sliced")
    near = low[max(0, m.start() - 20):m.end()]
    grade = next((g for g, pattern in GRADE_WORDS if g in s['grades'] and re.search(pattern, near)), None)
    start = max(0, m.start() - 20) if grade and not re.search(dict(GRADE_WORDS)[grade], w) else m.start()
    rest = re.sub(r'^[\s,;]+|[\s,;]+$', '', note[:start] + note[m.end():])
    rest = re.sub(r'\b(very|svært|veldig)\b\s*$', '', rest).strip(' ,;')
    rest = re.sub(r'\s*,(\s*,)+\s*', ', ', re.sub(r'\s{2,}', ' ', rest))
    return s['id'], grade, rest


def fill(data):
    """Give a recipe's lines their states, in place. Returns how many lines changed."""
    changed = 0
    method_of = {u: s.get('method') for s in data.get('steps') or [] if s.get('phase') == 'prep' for u in s.get('uses') or []}
    for line in data.get('ingredients') or []:
        if line.get('state'):
            continue
        state, grade, rest = (line.get('cut'), None, line.get('prep_style') or '') if line.get('cut') else from_text(line.get('prep_style'))
        if line.get('cut'):  # the old field: keep its id, and still take a grade and a note from prep_style
            _, grade, rest = from_text(line.get('prep_style'))
            if grade not in (by_id().get(state) or {}).get('grades', []):
                grade = None
        elif state and by_id()[state]['group'] in SOLD_SO and line.get('local_id') not in method_of:
            state, grade = None, None
        if not state:
            state = state_of_method(method_of.get(line.get('local_id')))
            rest = line.get('prep_style') or ''
        if not state:
            continue
        line['state'] = state
        line.pop('cut', None)
        if grade:
            line['grade'] = grade
        if rest:
            line['prep_style'] = rest
        else:
            line.pop('prep_style', None)
        changed += 1
    return changed
