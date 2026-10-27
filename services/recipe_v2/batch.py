"""Many new v2 recipes at once (/new-recipe/v2/batch): one line per recipe, read into what New Recipe would get.

    Butter chicken med kyllinglår i mild tomat- og fløtesaus, med basmatiris, for 4 | smart | kid
    Kjøttkaker i brun saus med potetmos og tyttebær, for 4 | classicist
    Søtpotetmos med linser | minimalist | baby 8
    # a line that starts with # is a note and is skipped

The idea first (one line, at most 200 characters, or a link to a recipe page), then, after "|", the chef and the
settings. A chef or setting left out takes the page's default. Chefs are known by any part of their id or name
(classicist, smart, minimalist; Klassikeren also works). Settings: vegetarian, kid, low carb, baby with its age
(baby 6, baby 8, baby 12), separated by commas or spaces. Nothing here starts a recipe; the route does.
"""
import re

from services.recipe_v2.persona import SETTINGS, age_stages
from services.recipe_v2.sources import is_link, is_video

IDEA_MAX = 200
MAX_LINES = 60
COST_EACH = (0.10, 0.40)  # USD for writing and structuring one recipe with Claude, from the pilot; images not included

# What people write for a setting -> the setting's key
SETTING_WORDS = {
    'vegetarian': 'vegetarian', 'vegetar': 'vegetarian', 'veg': 'vegetarian',
    'kid': 'kid_friendly', 'kids': 'kid_friendly', 'kid-friendly': 'kid_friendly', 'kid_friendly': 'kid_friendly',
    'barnevennlig': 'kid_friendly', 'barn': 'kid_friendly',
    'lowcarb': 'low_carb', 'low_carb': 'low_carb', 'low-carb': 'low_carb', 'lavkarbo': 'low_carb',
    'baby': 'baby',
}
CHEF_WORDS = {'klassiker': 'classicist', 'klassikeren': 'classicist', 'smarte': 'smart', 'minimalisten': 'minimalist'}


def _chef(word, chefs):
    """The chef a word names, or None. chefs: get_chefs()."""
    w = CHEF_WORDS.get(word.strip().lower(), word.strip().lower())
    if not w:
        return None
    hits = [c for c in chefs if w in c['id'].lower() or w in (c.get('name') or '').lower()]
    return hits[0] if len(hits) == 1 else None


def _settings(text):
    """(settings keys, baby's age or None, words not understood)"""
    words = re.sub(r'low\s+carb', 'lowcarb', text.lower())
    words = [w for w in re.split(r'[,\s]+', words) if w]
    keys, age, unknown = [], None, []
    ages = sorted(s['from_months'] for s in age_stages()['stages'])
    for w in words:
        if w.rstrip('m').isdigit() and keys and keys[-1] == 'baby':
            n = int(w.rstrip('m'))
            age = n if n in ages else None
            if age is None:
                unknown.append(f'baby {w}')
            continue
        key = SETTING_WORDS.get(w)
        if key and key in SETTINGS:
            if key not in keys:
                keys.append(key)
        else:
            unknown.append(w)
    if 'baby' in keys and age is None:
        age = ages[0]
    return keys, age, unknown


def parse(text, chefs, default_chef=None, default_settings=(), default_age=None, existing=None):
    """The lines as rows: {'no', 'source', 'kind', 'chef', 'settings', 'age', 'error', 'made'}. chefs: get_chefs().
    existing: {idea in lower case: recipe id} of recipes made before, so a line already made is marked."""
    rows = []
    for no, raw in enumerate((text or '').splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith('#'):
            continue
        parts = [p.strip() for p in line.split('|')]
        source, chef_word = parts[0], parts[1] if len(parts) > 1 else ''
        setting_text = ' '.join(parts[2:]) if len(parts) > 2 else ''
        row = {'no': no, 'source': source, 'kind': ('video' if is_video(source) else 'web') if is_link(source) else 'idea', 'chef': default_chef,
               'settings': list(default_settings), 'age': default_age, 'error': None,
               'made': (existing or {}).get(source.lower())}
        if chef_word:
            chef = _chef(chef_word, chefs)
            if chef is None:
                row['error'] = f'No single chef called "{chef_word}".'
            row['chef'] = chef
        if setting_text:
            keys, age, unknown = _settings(setting_text)
            row['settings'], row['age'] = keys, age
            if unknown:
                row['error'] = row['error'] or f"Unknown settings: {', '.join(unknown)}."
        if 'baby' not in row['settings']:
            row['age'] = None
        if not source:
            row['error'] = 'No idea before the "|".'
        elif row['kind'] == 'idea' and len(source) > IDEA_MAX:
            row['error'] = f'The idea is {len(source)} characters; at most {IDEA_MAX}. Paste a whole recipe in New Recipe instead.'
        if row['kind'] in ('web', 'video'):  # a recipe page or video is kept as it is: no chef style, no settings (as in New Recipe)
            row['settings'], row['age'] = [], None
        rows.append(row)
    return rows[:MAX_LINES], max(0, len(rows) - MAX_LINES)
