"""Fase 0b i docs/RECIPE_MODEL_V2.md: Claude mot Gemini på oppskriftsmodellen.

Samme 20 oppskrifter som fase 0 (scripts/pilot_v2.py), med promptreglene fra
pilotrapporten, kjørt med flere konfigurasjoner (modell og effort). I tillegg et
sett med kilder fra nettsider og video, som går gjennom hele kjeden: adapter,
runde 1 (normalisering) og runde 2 (strukturering).

Sett:
  fasit  De fem rettene, fra en kort beskrivelse (runde 1 skriver teksten).
  db     15 godkjente oppskrifter fra databasen (data/pilot_v2/inputs/db_recipes.json).
  web    Nettsider og videoer. Kildene hentes med --fetch og lagres utenfor repoet
         (PILOT0B_DIR, standard ~/promptlab-runs/pilot-0b), fordi repoet er offentlig
         og teksten tilhører andre. Resultatene for web lagres samme sted.

Bruk:
  python scripts/pilot_v2b.py --fetch URL [URL ...]          # henter kilder til web-settet
  python scripts/pilot_v2b.py --config sonnet-low --set all  # kjører en konfigurasjon
  python scripts/pilot_v2b.py --config all --set all
  python scripts/pilot_v2b.py --config opus-medium --set fasit --only carbonara
  python scripts/pilot_v2b.py --summary                      # tabellene fra lagrede resultater

Krever ANTHROPIC_API_KEY for Claude og GOOGLE_API_KEY for Gemini (og for video i --fetch).
Endrer ikke databasen. Kjøringer som finnes fra før, hoppes over; bruk --force for å kjøre på nytt.
"""
import argparse
import hashlib
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

import pilot_v2 as p0  # noqa: E402  (scripts/ is on sys.path when run as a script)
from services.ai_models import CLAUDE_OPUS, CLAUDE_SONNET  # noqa: E402
from services.recipe_v2_validator import format_errors_for_retry, validate_recipe_v2  # noqa: E402

RESULTS_DIR = ROOT / 'data' / 'pilot_v2' / 'results_0b'
PRIVATE_DIR = Path(os.getenv('PILOT0B_DIR', Path.home() / 'promptlab-runs' / 'pilot-0b'))
SOURCES = PRIVATE_DIR / 'sources.json'
MAX_RETRIES = p0.MAX_RETRIES
MAX_TOKENS = 32000

# provider, model, effort. Gemini runs the phase 0 code with the new prompt, as the baseline.
CONFIGS = {
    'gemini': ('gemini', p0.MODEL, None),
    'sonnet-low': ('claude', CLAUDE_SONNET, 'low'),
    'sonnet-high': ('claude', CLAUDE_SONNET, 'high'),
    'opus-low': ('claude', CLAUDE_OPUS, 'low'),
    'opus-medium': ('claude', CLAUDE_OPUS, 'medium'),
}
# USD per million tokens: input, output. Cache writes cost 1.25x input, cache reads 0.1x.
CLAUDE_PRICES = {CLAUDE_SONNET: (2.0, 10.0), CLAUDE_OPUS: (4.0, 20.0)}


# ---------- Claude ----------

def recipe_json_schema():
    """RecipeV2Schema as a JSON schema for structured output: every object closed, no titles."""
    from pydantic import TypeAdapter
    from schemas.recipe_v2 import RecipeV2Schema

    def clean(node):
        if isinstance(node, dict):
            node.pop('title', None)
            if node.get('type') == 'object':
                node['additionalProperties'] = False
            for v in node.values():
                clean(v)
        elif isinstance(node, list):
            for v in node:
                clean(v)
        return node

    return clean(TypeAdapter(RecipeV2Schema).json_schema())


def claude_usage(model, msg, seconds):
    u = msg.usage
    pin, pout = CLAUDE_PRICES[model]
    inp = u.input_tokens or 0
    cw = getattr(u, 'cache_creation_input_tokens', 0) or 0
    cr = getattr(u, 'cache_read_input_tokens', 0) or 0
    out = u.output_tokens or 0
    cost = (inp * pin + cw * pin * 1.25 + cr * pin * 0.1 + out * pout) / 1e6
    return {'model_version': msg.model, 'prompt_tokens': inp + cw + cr, 'cache_read_tokens': cr,
            'output_tokens': out, 'thought_tokens': None, 'stop_reason': msg.stop_reason,
            'cost_usd': round(cost, 6), 'seconds': round(seconds, 2)}


def claude_call(model, effort, system, messages, schema=None):
    """One streamed request. The system prompt (rules, catalogs, examples) is cached."""
    from services.ai_models import claude_client

    output_config = {'effort': effort}
    if schema:
        output_config['format'] = {'type': 'json_schema', 'schema': schema}
    kwargs = {'model': model, 'max_tokens': MAX_TOKENS, 'messages': messages, 'output_config': output_config}
    if system:
        kwargs['system'] = [{'type': 'text', 'text': system, 'cache_control': {'type': 'ephemeral'}}]
    t0 = time.time()
    with claude_client().messages.stream(**kwargs) as stream:
        msg = stream.get_final_message()
    return msg, claude_usage(model, msg, time.time() - t0)


def text_of(msg):
    return ''.join(b.text for b in msg.content if b.type == 'text')


def split_prompt(prompt):
    """The structure prompt ends with the source. Everything before it is the same for every recipe."""
    head, sep, source = prompt.rpartition('\nSOURCE RECIPE\n')
    if not sep:
        raise ValueError('structure.jinja2 must end with a "SOURCE RECIPE" section')
    return head, 'SOURCE RECIPE\n' + source


def claude_structure(model, effort, key, source):
    examples, prompt = p0.structure_prompt(key, source)
    system, user = split_prompt(prompt)
    schema = recipe_json_schema()
    messages = [{'role': 'user', 'content': user}]
    attempts, recipe = [], None
    for n in range(1 + MAX_RETRIES):
        msg, u = claude_call(model, effort, system, messages, schema)
        raw = text_of(msg)
        try:
            if msg.stop_reason in ('refusal', 'max_tokens'):
                raise ValueError(f'stop_reason {msg.stop_reason}')
            recipe = json.loads(raw)
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
        messages += [
            {'role': 'assistant', 'content': msg.content},
            {'role': 'user', 'content': 'Your answer failed validation:\n' + format_errors_for_retry(result) +
                                        '\n\nReturn the complete corrected recipe as JSON. Keep everything that was already correct.'},
        ]
    return recipe, attempts, examples


def claude_text(model, effort, prompt):
    msg, u = claude_call(model, effort, None, [{'role': 'user', 'content': prompt}])
    return text_of(msg), u


# ---------- round 1 per set ----------

def round1(config, set_name, key, source):
    """Returns (text for round 2, round 1 usage or None)."""
    provider, model, effort = CONFIGS[config]
    if set_name == 'db':
        return source, None
    if set_name == 'fasit':
        prompt = p0.env.get_template('recipe_v2/text.jinja2').render(description=p0.DESCRIPTIONS[key])
    else:
        prompt = p0.env.get_template('recipe_v2/normalize.jinja2').render(
            kind='a video' if source['kind'] == 'video' else 'a web page', source=source['text'])
    if provider == 'gemini':
        resp, u = p0.call(prompt)
        return resp.text, u
    return claude_text(model, effort, prompt)


def result_path(config, set_name, key):
    base = PRIVATE_DIR / 'results' if set_name == 'web' else RESULTS_DIR
    return base / config / set_name / f'{key}.json'


def run_one(config, set_name, key, source):
    provider, model, effort = CONFIGS[config]
    t0 = time.time()
    text, r1 = round1(config, set_name, key, source)
    if r1:
        print(f"  {key}: runde 1 ferdig ({r1['seconds']} s)", flush=True)
    if provider == 'gemini':
        recipe, attempts, examples = p0.structure(key, text)
    else:
        recipe, attempts, examples = claude_structure(model, effort, key, text)
    calls = ([r1] if r1 else []) + attempts
    out = {
        'key': key, 'set': set_name, 'config': config, 'model': model, 'effort': effort,
        'valid': attempts[-1]['valid'], 'attempts_used': len(attempts), 'first_try_valid': attempts[0]['valid'],
        'failed_rules_any_attempt': sorted({r for a in attempts for r in a['failed_rules']}, key=str),
        'model_version': attempts[-1]['model_version'], 'examples_in_prompt': examples,
        'tokens': {k: sum(c.get(k) or 0 for c in calls) for k in ('prompt_tokens', 'output_tokens', 'thought_tokens')},
        'cost_usd': round(sum(c['cost_usd'] for c in calls), 6),
        'api_seconds': round(sum(c['seconds'] for c in calls), 1), 'wall_seconds': round(time.time() - t0, 1),
        'round1': r1, 'attempts': attempts, 'source_text': text, 'recipe': recipe,
    }
    p0.save_json(result_path(config, set_name, key), out)
    return out


# ---------- sources from the web and video ----------

def source_key(url):
    return 'web-' + hashlib.sha1(url.encode()).hexdigest()[:8]


def fetch_sources(urls):
    sources = p0.load_json(SOURCES) if SOURCES.exists() else {}
    for url in urls:
        key = source_key(url)
        if key in sources:
            print(f'{key} finnes: {url}')
            continue
        if re.search(r'tiktok\.com|instagram\.com|youtube\.com|youtu\.be', url):
            sources[key] = fetch_video(url)
        else:
            from services.web_scraper_service import WebScraper
            page = WebScraper().scrape_url(url)
            sources[key] = {'kind': 'web', 'url': url, 'text': page['text']}
        print(f"{key} {sources[key]['kind']}: {len(sources[key]['text'])} tegn fra {url}")
        p0.save_json(SOURCES, sources)
    return sources


def fetch_video(url):
    """The video adapter from RECIPE_MODEL_V2.md: download, then Gemini turns the video into text."""
    from google.genai import types
    from services.ai_models import GEMINI_TEXT, gemini_client
    from services.social_media_service import SocialMediaExtractor

    video = SocialMediaExtractor.download_video(url)
    try:
        client = gemini_client()
        ref = client.files.upload(file=video['video_path'])
        while ref.state and ref.state.name == 'PROCESSING':
            time.sleep(3)
            ref = client.files.get(name=ref.name)
        prompt = p0.env.get_template('recipe_v2/video_text.jinja2').render(caption=video['caption'])
        resp = client.models.generate_content(
            model=GEMINI_TEXT, contents=[types.Part.from_uri(file_uri=ref.uri, mime_type=ref.mime_type), prompt])
        return {'kind': 'video', 'url': url, 'caption': video['caption'], 'text': resp.text}
    finally:
        SocialMediaExtractor.cleanup(video['video_path'], video.get('thumbnail_path'))


# ---------- checks for the pilot's findings ----------

EACH = re.compile(r'\{i\d+\}[^.{}]{0,40}\b(each|per|hver|hvert|på hver|i hver|apiece)\b'
                  r'|\b(each|hver|på hver|i hver)\b[^.{}]{0,20}\{i\d+\}', re.IGNORECASE)
NOT_COMPONENTS = re.compile(r'assembl|garnish|main dish|topping|sammensett|montering|pynt|servering|serving',
                            re.IGNORECASE)


def findings(recipe):
    """Counts for the problems the phase 0 review found, which the validator does not reject."""
    steps = recipe.get('steps') or []
    referenced = {a for s in steps for a in s.get('after') or []}
    finals = [s for s in steps if s.get('local_id') not in referenced and (s.get('uses') or s.get('after'))]
    result = validate_recipe_v2(recipe)
    return {
        'each_with_total': sum(bool(EACH.search(s.get('text') or '')) for s in steps),
        'final_not_serve': int(bool(finals) and finals[0].get('phase') != 'serve'),
        'bad_components': [c['name'] for c in recipe.get('components') or [] if NOT_COMPONENTS.search(c.get('name') or '')],
        'loose_equipment_steps': sum(1 for s in steps if not s.get('uses') and not s.get('after') and not s.get('setup')),
        'no_preheat': sum(1 for w in result['warnings'] if w['code'] == 'no_preheat'),
        'steps': len(steps), 'components': len(recipe.get('components') or []),
    }


def faithfulness(recipe, source_recipe):
    """Ingredients and amounts against the database source: missing, added, changed (by pantry id)."""
    src, out = {}, {}
    for i in source_recipe['ingredients']:
        k = i.get('food_id') or (i.get('name') or '').lower()
        src[k] = src.get(k, 0) + (i.get('amount') or 0)
    for i in recipe.get('ingredients') or []:
        k = i.get('pantry_id') or (i.get('name') or '').lower()
        out[k] = out.get(k, 0) + (i.get('amount') or 0)
    changed = [k for k in src if k in out and src[k] and abs(out[k] - src[k]) / src[k] > 0.05]
    return {'missing': [k for k in src if k not in out], 'added': [k for k in out if k not in src], 'amount_changed': changed}


# ---------- summary ----------

def load_results():
    out = []
    for base in (RESULTS_DIR, PRIVATE_DIR / 'results'):
        if base.is_dir():
            out += [p0.load_json(f) for f in sorted(base.glob('*/*/*.json'))]
    return out


def summary(results):
    db_sources = {f"db-{r['id']}": r for r in p0.load_json(p0.DB_INPUT)} if os.path.exists(p0.DB_INPUT) else {}
    order = list(CONFIGS)
    lines = ['| Konfigurasjon | Sett | Bestått | Første forsøk | Snitt USD | Snitt s | Maks s | «hver» med total | '
             'Sluttsteg ikke serve | Ugyldige komponenter | Ovn uten forvarming | Trofasthet (mangler/lagt til/endret) |',
             '|---|---|---|---|---|---|---|---|---|---|---|---|']
    for config in sorted({r['config'] for r in results}, key=order.index):
        for set_name in ('fasit', 'db', 'web', 'alle'):
            rs = [r for r in results if r['config'] == config and (set_name == 'alle' or r['set'] == set_name)]
            if not rs:
                continue
            f = [findings(r['recipe']) for r in rs if r.get('recipe')]
            fa = [faithfulness(r['recipe'], db_sources[r['key']]) for r in rs if r.get('recipe') and r['key'] in db_sources]
            faith = (f"{sum(len(x['missing']) for x in fa)}/{sum(len(x['added']) for x in fa)}/"
                     f"{sum(len(x['amount_changed']) for x in fa)}") if fa else '–'
            lines.append(
                f"| {config} | {set_name} | {sum(r['valid'] for r in rs)}/{len(rs)} | {sum(r['first_try_valid'] for r in rs)}/{len(rs)} | "
                f"{sum(r['cost_usd'] for r in rs) / len(rs):.3f} | {sum(r['wall_seconds'] for r in rs) / len(rs):.0f} | "
                f"{max(r['wall_seconds'] for r in rs):.0f} | {sum(x['each_with_total'] for x in f)} | "
                f"{sum(x['final_not_serve'] for x in f)} | {sum(len(x['bad_components']) for x in f)} | "
                f"{sum(x['no_preheat'] for x in f)} | {faith} |")
    total = sum(r['cost_usd'] for r in results)
    return '\n'.join(lines + ['', f'Total kostnad: {total:.2f} USD for {len(results)} kjøringer.'])


# ---------- command line ----------

def jobs_for(set_name, only):
    jobs = []
    if set_name in ('fasit', 'all'):
        jobs += [('fasit', k, None) for k in p0.DESCRIPTIONS]
    if set_name in ('db', 'all'):
        jobs += [('db', f"db-{r['id']}", p0.db_source_text(r)) for r in p0.load_json(p0.DB_INPUT)]
    if set_name in ('web', 'all') and SOURCES.exists():
        jobs += [('web', k, s) for k, s in p0.load_json(SOURCES).items()]
    if only:
        keep = set(only.split(','))
        jobs = [j for j in jobs if j[1] in keep]
    return jobs


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--fetch', nargs='+', metavar='URL', help='hent kilder til web-settet')
    ap.add_argument('--config', help='kommaseparert, eller all: ' + ', '.join(CONFIGS))
    ap.add_argument('--set', choices=['fasit', 'db', 'web', 'all'])
    ap.add_argument('--only', help='kommaseparert liste med nøkler (carbonara, db-155, web-1a2b3c4d)')
    ap.add_argument('--workers', type=int, default=3)
    ap.add_argument('--force', action='store_true', help='kjør på nytt selv om resultatet finnes')
    ap.add_argument('--summary', action='store_true')
    args = ap.parse_args(argv)

    if args.fetch:
        fetch_sources(args.fetch)
    if args.config and args.set:
        configs = list(CONFIGS) if args.config == 'all' else args.config.split(',')
        unknown = [c for c in configs if c not in CONFIGS]
        if unknown:
            sys.exit(f'Ukjent konfigurasjon: {", ".join(unknown)}. Velg blant {", ".join(CONFIGS)}.')
        for config in configs:
            jobs = [j for j in jobs_for(args.set, args.only)
                    if args.force or not result_path(config, j[0], j[1]).exists()]
            print(f'{config}: {len(jobs)} oppskrifter', flush=True)
            with ThreadPoolExecutor(max_workers=args.workers) as ex:
                list(ex.map(lambda j: run_one(config, *j), jobs))
    if args.summary or (args.config and args.set):
        text = summary(load_results())
        p0.save_json(RESULTS_DIR / 'summary.json', {'markdown': text})
        print(text)


if __name__ == '__main__':
    main()
