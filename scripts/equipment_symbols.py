"""Symbols for the equipment bank (data/constraints/equipment.json), in the style of the ingredient symbols.

    python scripts/equipment_symbols.py generate --pilot            # eight items, to check the style at small sizes
    python scripts/equipment_symbols.py generate                    # every item that gets a symbol
    python scripts/equipment_symbols.py generate --run <dir> --only whisk,grater --notes <json>   # again, with notes
    python scripts/equipment_symbols.py generate --pilot --style painted --run <dir>   # the pilot in another style
    python scripts/equipment_symbols.py promote --run <dir> [--style painted]   # upload and set image (or image_variants[style])

generate writes the images and sheet.png (each symbol large, at 48 px and at 32 px) to
~/promptlab-runs/equipment-<time>; it is resumable and does what is missing. --notes is a JSON file
{id: "what to change"}, added to the item's image_notes for that run. promote uploads every image of the run
that is not listed in rejected.json as 512 px WebP to gs://thelazychef-assets/equipment/symbols/<run>/ and sets
"image" in equipment.json; commit that on a branch.

The prompt is the lab task data/prompts/lab/equipment_image ([final]). Supplies (foil, plates) and items shown as
another one (same_as) get no symbol. generate needs GOOGLE_API_KEY (about USD 0.04 an image); promote needs gcloud.
"""
import argparse
import datetime
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from promptlab.run import RUNS_DIR  # noqa: E402

CATALOG = ROOT / 'data' / 'constraints' / 'equipment.json'
BUCKET = 'thelazychef-assets'
PROJECT = 'thelazychefai-prod'
PILOT = ['oven', 'frying_pan', 'saucepan', 'whisk', 'grater', 'stick_blender', 'ovenproof_dish', 'colander']


def items():
    """The items that get a symbol: not supplies, not shown as another one."""
    return [e for e in json.loads(CATALOG.read_text())['equipment'] if e.get('kind') != 'supply' and not e.get('same_as')]


def prompt_for(e, extra='', style=None):
    """The prompt from the lab task's [final] variants; style picks another style layer (a file in style/)."""
    from promptlab.compose import load_task

    task = load_task('equipment_image')
    notes = ' '.join(x for x in (e.get('image_notes'), extra) if x)
    choice = dict(task.final, style=style) if style else task.final
    return task.compose(choice, {'name': (e.get('name_en') or e['name']).lower(), 'notes': notes})


def generate(run, only=None, pilot=False, notes=None, workers=4, style=None):
    from services.image_generation import generate_image

    manifest_path = run / 'manifest.json'
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    wanted = [e for e in items() if (not pilot or e['id'] in PILOT) and (only is None or e['id'] in only)]
    todo = [e for e in wanted if only is not None or e['id'] not in manifest]
    print(f'{len(todo)} of {len(wanted)} symbols to make')
    (run / 'images').mkdir(parents=True, exist_ok=True)

    def work(e):
        prompt = prompt_for(e, (notes or {}).get(e['id'], ''), style)
        png, _ = generate_image(prompt)
        version = manifest.get(e['id'], {}).get('version', 0) + 1
        path = run / 'images' / f"{e['id']}-v{version}.png"
        path.write_bytes(png)
        return e['id'], {'name': e.get('name_en') or e['name'], 'version': version, 'image': str(path.relative_to(run)), 'prompt': prompt}

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for key, entry in pool.map(work, todo):
            manifest[key] = entry
            manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
            print(f'  {key}', flush=True)
    sheet(run, manifest)


def sheet(run, manifest):
    """sheet.png: each symbol at 180 px, and the same at 48 and 32 px under it, to judge them at small sizes."""
    from PIL import Image, ImageDraw

    keys = sorted(manifest)
    cols, cell = 6, 220
    rows = (len(keys) + cols - 1) // cols
    out = Image.new('RGB', (cols * cell, rows * (cell + 70)), 'white')
    draw = ImageDraw.Draw(out)
    for n, key in enumerate(keys):
        x, y = (n % cols) * cell, (n // cols) * (cell + 70)
        im = Image.open(run / manifest[key]['image']).convert('RGB')
        big = im.copy()
        big.thumbnail((180, 180))
        out.paste(big, (x + 20, y + 10))
        for size, dx in ((48, 30), (32, 100)):
            small = im.resize((size, size), Image.LANCZOS)
            out.paste(small, (x + dx, y + 195))
        draw.text((x + 20, y + 250), key, fill='black')
    out.save(run / 'sheet.png')
    print(f"Sheet: {run / 'sheet.png'}")


def promote(run, style=None):
    """style None (or realistic) sets "image"; another style sets "image_variants"[style]."""
    from services.ingredient_symbols import web_image

    manifest = json.loads((run / 'manifest.json').read_text())
    rejected = set(json.loads((run / 'rejected.json').read_text())) if (run / 'rejected.json').exists() else set()
    web = run / 'web'
    web.mkdir(exist_ok=True)
    urls = {}
    for key, entry in manifest.items():
        if key in rejected:
            continue
        name = f"{key}-v{entry['version']}.webp"
        (web / name).write_bytes(web_image((run / entry['image']).read_bytes()))
        urls[key] = f'https://storage.googleapis.com/{BUCKET}/equipment/symbols/{run.name}/{name}'
    subprocess.run(['gcloud', 'storage', 'cp', '--recursive', f'{web}/*', f'gs://{BUCKET}/equipment/symbols/{run.name}/',
                    f'--project={PROJECT}'], check=True)
    catalog = json.loads(CATALOG.read_text())
    for e in catalog['equipment']:
        if e['id'] in urls:
            if style and style != 'realistic':
                e.setdefault('image_variants', {})[style] = urls[e['id']]
            else:
                e['image'] = urls[e['id']]
    CATALOG.write_text(json.dumps(catalog, indent=2, ensure_ascii=False) + '\n')
    print(f'{len(urls)} symbols uploaded and set in {CATALOG.relative_to(ROOT)}; {len(rejected)} rejected left out.')


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('command', choices=('generate', 'promote'))
    p.add_argument('--run', type=Path)
    p.add_argument('--pilot', action='store_true')
    p.add_argument('--only', help='comma separated ids to make (again)')
    p.add_argument('--notes', type=Path, help='JSON {id: what to change}')
    p.add_argument('--style', help='another style layer from the lab task (illustrated, painted, line_tint, risograph)')
    args = p.parse_args()
    if args.command == 'promote':
        if not args.run:
            raise SystemExit('Give --run')
        promote(args.run, args.style)
        return
    run = args.run or RUNS_DIR / f"equipment-{datetime.datetime.now():%Y%m%d-%H%M}"
    print(f'Run: {run}')
    notes = json.loads(args.notes.read_text()) if args.notes else None
    generate(run, only=set(args.only.split(',')) if args.only else None, pilot=args.pilot, notes=notes, style=args.style)


if __name__ == '__main__':
    main()
