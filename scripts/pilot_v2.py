"""Fase 0 i docs/RECIPE_MODEL_V2.md: klarer Gemini å lage oppskrifter i grafmodellen?

For hver oppskrift: strukturer (runde 2), valider, prøv på nytt med feilmeldingene
maks to ganger, og lagre JSON-resultatet med tokens, kostnad og tid.

Testsett:
  fasit  De fem rettene fra docs/prototypes/fem-retter.html, generert fra en kort
         beskrivelse gjennom runde 1 (tekst) og runde 2 (strukturering).
  db     15 godkjente oppskrifter fra databasen, strukturert fra dagens ingredienser
         og steg. Hentes først med --export-db (krever databasetilgang), så kjøringen
         kan gjentas uten database.

Bruk:
  python scripts/pilot_v2.py --export-db              # henter 15 godkjente oppskrifter
  python scripts/pilot_v2.py --set all                # kjører piloten
  python scripts/pilot_v2.py --set fasit --only carbonara
  python scripts/pilot_v2.py --summary                # skriver tabellene på nytt fra lagrede resultater

Leser GOOGLE_API_KEY fra miljøet eller .env, som appen. Endrer ikke databasen.
"""
import argparse
import json
import os
import random
import sys
import time
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from jinja2 import Environment, FileSystemLoader  # noqa: E402

from services.recipe_v2_validator import RULES, format_errors_for_retry, validate_recipe_v2  # noqa: E402

MODEL = 'gemini-flash-latest'  # samme som generate_recipe_ai i ai_engine.py
MAX_RETRIES = 2
PILOT_DIR = os.path.join(ROOT, 'data', 'pilot_v2')
RESULTS_DIR = os.path.join(PILOT_DIR, 'results')
DB_INPUT = os.path.join(PILOT_DIR, 'inputs', 'db_recipes.json')
FASIT_DIR = os.path.join(PILOT_DIR, 'fasit')

# USD per million tokens (input, output inkl. tenketokens). Prisen velges ut fra model_version i svaret.
PRICES = [
    ('gemini-3-flash', 0.50, 3.00),
    ('gemini-2.5-flash-lite', 0.10, 0.40),
    ('gemini-2.5-flash', 0.30, 2.50),
]
FALLBACK_PRICE = ('ukjent, regnet som gemini-3-flash', 0.50, 3.00)

DESCRIPTIONS = {
    'carbonara': 'Spaghetti carbonara på klassisk vis med guanciale, egg og eggeplommer, pecorino romano og sort pepper. 4 porsjoner.',
    'brownies': 'Brownies med mørk sjokolade og valnøtter, stekt i en form på 20 × 20 cm og skåret i 16 biter.',
    'tikka': 'Kylling tikka masala med marinert kyllinglår som grilles i ovnen, servert med basmatiris. 4 porsjoner.',
    'lasagne': 'Lasagne med kjøttsaus og hvit saus, servert med en grønn salat med dressing. 4 porsjoner.',
    'burger': 'Hamburgere med hjemmelagde hamburgerbrød, cheddar og topping, servert med pommes frites stekt i ovnen. 4 porsjoner.',
}
# Eksemplene i promptet er carbonara og lasagne. Når en av dem selv struktureres, byttes eksemplet ut
# så modellen ikke ser fasiten.
DEFAULT_EXAMPLES = ['carbonara', 'lasagne']
SWAP_EXAMPLE = {'carbonara': 'tikka', 'lasagne': 'brownies'}

env = Environment(loader=FileSystemLoader(os.path.join(ROOT, 'data', 'prompts')))
_client = None


def client():
    global _client
    if _client is None:
        from dotenv import load_dotenv
        from google import genai
        load_dotenv()
        key = os.getenv('GOOGLE_API_KEY')
        if not key:
            sys.exit('GOOGLE_API_KEY mangler. Legg den i .env eller miljøet, som for appen.')
        _client = genai.Client(api_key=key)
    return _client


def load_json(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write('\n')


# ---------- prompt ----------

def catalogs_for_prompt():
    c = os.path.join(ROOT, 'data', 'constraints')
    methods = load_json(os.path.join(c, 'methods.json'))['methods']
    eq = load_json(os.path.join(c, 'equipment.json'))['equipment']
    units = load_json(os.path.join(c, 'units.json'))['units']
    return {
        'methods': ', '.join(m['id'] + (' [heat]' if m['heat'] else '') for m in methods),
        'equipment': ', '.join(f"{e['id']} ({e['name']})" for e in eq),
        'units': ', '.join(f"{u['id']} ({u['name']})" if u['name'] != u['id'] else u['id'] for u in units),
    }


def examples_for(key):
    names = [SWAP_EXAMPLE.get(n, n) if n == key else n for n in DEFAULT_EXAMPLES]
    out = []
    for n in names:
        r = load_json(os.path.join(FASIT_DIR, n + '.json'))
        out.append({'title': r['title'], 'json': json.dumps(r, ensure_ascii=False, separators=(',', ':'))})
    return names, out


def structure_prompt(key, source):
    names, examples = examples_for(key)
    return names, env.get_template('recipe_v2/structure.jinja2').render(
        source=source, examples=examples, **catalogs_for_prompt())


def db_source_text(r):
    lines = [f"Title: {r['title']}", f"Servings: {r['servings']}", '', 'Ingredients (component | amount unit | name | prep_style | pantry food_id):']
    for i in r['ingredients']:
        amt = '' if i.get('amount') in (None, 0) else f"{i['amount']:g} {i.get('unit') or ''}".strip()
        lines.append(f"- {i.get('component') or ''} | {amt} | {i['name']} | {i.get('prep_style') or ''} | {i.get('food_id') or ''}")
    lines += ['', 'Steps in order (component | phase | minutes | text):']
    for n, s in enumerate(r['steps'], 1):
        lines.append(f"{n}. {s.get('component') or ''} | {s.get('phase') or ''} | {s.get('estimated_minutes') or ''} | {s['text']}")
    return '\n'.join(lines)


# ---------- Gemini ----------

def price_for(model_version):
    for prefix, pin, pout in PRICES:
        if (model_version or '').startswith(prefix):
            return prefix, pin, pout
    return FALLBACK_PRICE


def usage(resp, seconds):
    u = resp.usage_metadata
    p = getattr(u, 'prompt_token_count', 0) or 0
    c = getattr(u, 'candidates_token_count', 0) or 0
    t = getattr(u, 'thoughts_token_count', 0) or 0
    mv = getattr(resp, 'model_version', None) or MODEL
    _, pin, pout = price_for(mv)
    return {'model_version': mv, 'prompt_tokens': p, 'output_tokens': c, 'thought_tokens': t,
            'cost_usd': round((p * pin + (c + t) * pout) / 1e6, 6), 'seconds': round(seconds, 2)}


def call(contents, schema=None):
    from google.genai import types
    cfg = types.GenerateContentConfig(response_mime_type='application/json', response_schema=schema) if schema else None
    for attempt in range(4):
        t0 = time.time()
        try:
            resp = client().models.generate_content(model=MODEL, contents=contents, config=cfg)
            return resp, usage(resp, time.time() - t0)
        except Exception as e:  # nettverk, kvote: vent og prøv igjen, teller ikke som forsøk
            if attempt == 3:
                raise
            print(f'  API-feil ({e.__class__.__name__}: {str(e)[:120]}), venter …', flush=True)
            time.sleep(10 * (attempt + 1))


def round1_text(key):
    prompt = env.get_template('recipe_v2/text.jinja2').render(description=DESCRIPTIONS[key])
    resp, u = call(prompt)
    return resp.text, u


def structure(key, source):
    from google.genai import types
    from schemas.recipe_v2 import RecipeV2Schema

    examples, prompt = structure_prompt(key, source)
    contents = [types.Content(role='user', parts=[types.Part(text=prompt)])]
    attempts = []
    recipe = None
    for n in range(1 + MAX_RETRIES):
        resp, u = call(contents, RecipeV2Schema)
        raw = resp.text or ''
        try:
            recipe = resp.parsed if isinstance(resp.parsed, dict) else json.loads(raw)
            result = validate_recipe_v2(recipe)
        except Exception as e:
            recipe = None
            result = {'valid': False, 'failed_rules': ['json'], 'warnings': [],
                      'errors': [{'rule': 'json', 'message': f'The answer was not valid JSON: {e}'}]}
        attempts.append({'attempt': n + 1, 'valid': result['valid'], 'failed_rules': result['failed_rules'],
                         'errors': result['errors'], 'warnings': result['warnings'], **u})
        print(f"  {key}: forsøk {n + 1} {'OK' if result['valid'] else 'feil ' + str(result['failed_rules'])}"
              f" ({u['seconds']} s)", flush=True)
        if result['valid']:
            break
        contents += [
            types.Content(role='model', parts=[types.Part(text=raw)]),
            types.Content(role='user', parts=[types.Part(text=(
                'Your answer failed validation:\n' + format_errors_for_retry(result) +
                '\n\nReturn the complete corrected recipe as JSON. Keep everything that was already correct.'))]),
        ]
    return recipe, attempts, examples


def run_one(set_name, key, source=None):
    t0 = time.time()
    r1 = None
    if set_name == 'fasit':
        source, r1 = round1_text(key)
        print(f"  {key}: runde 1 ferdig ({r1['seconds']} s)", flush=True)
    recipe, attempts, examples = structure(key, source)
    calls = ([r1] if r1 else []) + attempts
    out = {
        'key': key, 'set': set_name, 'valid': attempts[-1]['valid'], 'attempts_used': len(attempts),
        'first_try_valid': attempts[0]['valid'], 'failed_rules_any_attempt': sorted({r for a in attempts for r in a['failed_rules']}, key=str),
        'model_version': attempts[-1]['model_version'], 'examples_in_prompt': examples,
        'tokens': {k: sum(c[k] for c in calls) for k in ('prompt_tokens', 'output_tokens', 'thought_tokens')},
        'cost_usd': round(sum(c['cost_usd'] for c in calls), 6),
        'api_seconds': round(sum(c['seconds'] for c in calls), 1), 'wall_seconds': round(time.time() - t0, 1),
        'round1': r1, 'attempts': attempts, 'source_text': source, 'recipe': recipe,
    }
    save_json(os.path.join(RESULTS_DIR, set_name, key + '.json'), out)
    return out


# ---------- database ----------

def export_db(n=15, seed=42):
    from dotenv import load_dotenv
    from flask import Flask
    load_dotenv()
    from database.db_connector import configure_database
    from database.models import Recipe, db

    app = Flask(__name__)
    configure_database(app)
    db.init_app(app)
    with app.app_context():
        recipes = db.session.query(Recipe).filter(Recipe.status == 'approved').order_by(Recipe.id).all()
        print(f'{len(recipes)} godkjente oppskrifter, velger {min(n, len(recipes))} (frø {seed})')
        picked = sorted(random.Random(seed).sample(recipes, min(n, len(recipes))), key=lambda r: r.id)
        out = []
        for r in picked:
            steps = sorted(r.instructions, key=lambda s: (s.global_order_index if s.global_order_index is not None else 10_000, s.step_number))
            out.append({
                'id': r.id, 'title': r.title, 'servings': r.base_servings,
                'ingredients': [{'component': i.component, 'amount': i.amount, 'unit': i.unit, 'prep_style': i.prep_style,
                                 'name': i.ingredient.name if i.ingredient else None,
                                 'food_id': i.ingredient.food_id if i.ingredient else None} for i in r.ingredients],
                'steps': [{'component': s.component, 'phase': s.phase, 'step_number': s.step_number,
                           'global_order_index': s.global_order_index, 'estimated_minutes': s.estimated_minutes,
                           'text': s.text} for s in steps],
            })
    save_json(DB_INPUT, out)
    print('skrev', os.path.relpath(DB_INPUT, ROOT))


# ---------- oppsummering ----------

def load_results():
    out = []
    for set_name in ('fasit', 'db'):
        d = os.path.join(RESULTS_DIR, set_name)
        if os.path.isdir(d):
            out += [load_json(os.path.join(d, f)) for f in sorted(os.listdir(d)) if f.endswith('.json')]
    return out


def summary(results):
    def pct(a, b):
        return f'{a}/{b} ({100 * a / b:.0f} %)' if b else '–'

    lines = ['| Sett | Oppskrift | Bestått | Forsøk | Regler som feilet underveis | Tokens inn/ut/tenk | Kostnad (USD) | Tid (s) |',
             '|---|---|---|---|---|---|---|---|']
    for r in results:
        t = r['tokens']
        lines.append(f"| {r['set']} | {r['recipe']['title'] if r.get('recipe') else r['key']} | {'ja' if r['valid'] else 'nei'} | {r['attempts_used']} | "
                     f"{', '.join(map(str, r['failed_rules_any_attempt'])) or '–'} | {t['prompt_tokens']}/{t['output_tokens']}/{t['thought_tokens']} | "
                     f"{r['cost_usd']:.4f} | {r['wall_seconds']} |")
    agg = ['', '| Sett | Bestått etter nye forsøk | Bestått i første forsøk | Snitt kostnad (USD) | Snitt tid (s) | Maks tid (s) |', '|---|---|---|---|---|---|']
    for name, rs in (('fasit', [r for r in results if r['set'] == 'fasit']), ('db', [r for r in results if r['set'] == 'db']), ('alle', results)):
        if not rs:
            continue
        agg.append(f"| {name} | {pct(sum(r['valid'] for r in rs), len(rs))} | {pct(sum(r['first_try_valid'] for r in rs), len(rs))} | "
                   f"{sum(r['cost_usd'] for r in rs) / len(rs):.4f} | {sum(r['wall_seconds'] for r in rs) / len(rs):.0f} | {max(r['wall_seconds'] for r in rs):.0f} |")
    counts = {}
    for r in results:
        for a in r['attempts']:
            for rule in a['failed_rules']:
                counts.setdefault(rule, [0, 0])
                counts[rule][0] += 1
        for rule in r['failed_rules_any_attempt']:
            counts.setdefault(rule, [0, 0])
            counts[rule][1] += 1
    rl = ['', '| Regel | Beskrivelse | Forsøk som feilet | Oppskrifter berørt |', '|---|---|---|---|']
    for rule, (na, nr) in sorted(counts.items(), key=lambda x: -x[1][0]):
        rl.append(f"| {rule} | {RULES.get(rule, 'Ugyldig JSON') if rule != 'json' else 'Ugyldig JSON'} | {na} | {nr} |")
    versions = sorted({r['model_version'] for r in results})
    prices = [f'{v}: {price_for(v)[1]} / {price_for(v)[2]} USD per million tokens inn/ut ({price_for(v)[0]})' for v in versions]
    return '\n'.join(agg + rl + ['', *lines, '', 'Modell: ' + '; '.join(prices)])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--set', choices=['fasit', 'db', 'all'], default=None)
    ap.add_argument('--only', help='kommaseparert liste med nøkler (carbonara, db-42 …)')
    ap.add_argument('--export-db', action='store_true')
    ap.add_argument('--summary', action='store_true')
    ap.add_argument('--workers', type=int, default=4)
    args = ap.parse_args()

    if args.export_db:
        export_db()
    if args.set:
        jobs = []
        if args.set in ('fasit', 'all'):
            jobs += [('fasit', k, None) for k in DESCRIPTIONS]
        if args.set in ('db', 'all'):
            if not os.path.exists(DB_INPUT):
                sys.exit(f'Mangler {os.path.relpath(DB_INPUT, ROOT)}. Kjør med --export-db først.')
            jobs += [('db', f"db-{r['id']}", db_source_text(r)) for r in load_json(DB_INPUT)]
        if args.only:
            keep = set(args.only.split(','))
            jobs = [j for j in jobs if j[1] in keep]
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            list(ex.map(lambda j: run_one(*j), jobs))
    if args.summary or args.set:
        text = summary(load_results())
        save_json(os.path.join(RESULTS_DIR, 'summary.json'), {'markdown': text})
        print(text)


if __name__ == '__main__':
    main()
