"""Samples for the dish image lab task: the fasit recipes as services/recipe_v2/appearance.py describes them.

    python -m scripts.dish_image_samples                      # all five fasit recipes
    python -m scripts.dish_image_samples carbonara lasagne    # some of them
    python -m scripts.dish_image_samples --file my_recipe.json

Writes data/prompts/lab/dish_image/samples.toml (set "default"). Needs ANTHROPIC_API_KEY and costs about
0.01 USD per recipe. Then try the styles: python -m promptlab run dish_image --vary style=editorial,overhead,cutout,illustrated
"""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from services.recipe_v2.appearance import describe  # noqa: E402

FASIT = ['carbonara', 'lasagne', 'tikka', 'brownies', 'burger']
OUT = os.path.join(ROOT, 'data', 'prompts', 'lab', 'dish_image', 'samples.toml')


def toml_string(s):
    return json.dumps(s, ensure_ascii=False)  # JSON escapes are valid in TOML basic strings


def to_toml(samples):
    rows = []
    for s in samples:
        comps = ', '.join(f"{{ name = {toml_string(c['name'])}, appearance = {toml_string(c['appearance'])} }}"
                          for c in s['components'])
        rows.append(f"  {{ id = {toml_string(s['id'])}, title = {toml_string(s['title'])}, "
                    f"plating = {toml_string(s['plating'])}, components = [{comps}] }},")
    return ('# Made by scripts/dish_image_samples.py from the fasit recipes; run it again rather than editing.\n'
            'default = [\n' + '\n'.join(rows) + '\n]\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('names', nargs='*', help=f"fasit recipes ({', '.join(FASIT)})")
    parser.add_argument('--file', action='append', default=[], help='a recipe in v2 JSON')
    args = parser.parse_args()
    paths = [(n, os.path.join(ROOT, 'data', 'pilot_v2', 'fasit', n + '.json')) for n in (args.names or ([] if args.file else FASIT))]
    paths += [(os.path.splitext(os.path.basename(f))[0], f) for f in args.file]
    samples, cost = [], 0.0
    for name, path in paths:
        with open(path, encoding='utf-8') as f:
            v2 = json.load(f)
        look, usage = describe(v2)
        cost += usage.get('cost_usd') or 0
        samples.append({'id': name, 'title': v2['title'], **look})
        print(f"{name}: {look['plating']}")
        for c in look['components']:
            print(f"  {c['name']}: {c['appearance']}")
    with open(OUT, 'w', encoding='utf-8') as f:
        f.write(to_toml(samples))
    print(f'\nWrote {len(samples)} samples to {os.path.relpath(OUT, ROOT)}. Cost {cost:.3f} USD.')


if __name__ == '__main__':
    main()
