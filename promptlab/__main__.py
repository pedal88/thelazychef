"""python -m promptlab list | render | run | score   (see docs/PROMPT_LAB.md)"""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from promptlab.compose import LAB_DIR, load_task  # noqa: E402
from promptlab.run import RUNS_DIR, merge_scores, plan, resolve_models, run  # noqa: E402


def parse_vary(items: list[str]) -> dict[str, list[str]]:
    vary = {}
    for item in items or []:
        layer, _, values = item.partition('=')
        if not values:
            raise SystemExit(f"--vary needs layer=variant[,variant]: {item}")
        vary[layer] = [v for v in values.split(',') if v]
    return vary


def main(argv=None):
    parser = argparse.ArgumentParser(prog='python -m promptlab')
    sub = parser.add_subparsers(dest='command', required=True)

    sub.add_parser('list', help='tasks, layers, variants and sample sets')

    for name in ('render', 'run'):
        p = sub.add_parser(name, help='print prompts' if name == 'render' else 'run and save a contact sheet')
        p.add_argument('task')
        p.add_argument('--vary', action='append', metavar='LAYER=A,B', help='variants to compare (repeatable)')
        p.add_argument('--sample', default='default', help='sample set in samples.toml')
        p.add_argument('--limit', type=int, help='first N samples only')
        p.add_argument('--models', help='compare models: constants from services/ai_models.py or model IDs, comma separated')
        if name == 'run':
            p.add_argument('--dry-run', action='store_true', help='build prompts and the sheet, call no model')

    p = sub.add_parser('score', help='copy scores exported from sheet.html into run.json')
    p.add_argument('run_folder', type=Path)
    p.add_argument('scores', type=Path)

    args = parser.parse_args(argv)

    if args.command == 'list':
        for path in sorted(p for p in LAB_DIR.iterdir() if (p / 'task.toml').exists()):
            task = load_task(path.name)
            print(f"{task.name}  ({task.kind}, {task.model})")
            for layer in task.layers:
                print(f"  {layer}: {', '.join(task.variants(layer))}")
            print(f"  samples: {', '.join(f'{k} ({len(v)})' for k, v in task.sample_sets.items())}")
        return

    if args.command == 'score':
        count = merge_scores(args.run_folder, args.scores)
        print(f"{count} cells scored in {args.run_folder / 'run.json'}")
        return

    task = load_task(args.task)
    vary = parse_vary(args.vary)
    models = [m for m in args.models.split(',') if m] if args.models else None

    if args.command == 'render':
        for cell in plan(task, vary, args.sample, args.limit, resolve_models(task, models)):
            print(f"--- {cell['sample']} [{cell['variant']}]\n{cell['prompt']}\n")
        return

    folder = run(task, vary, args.sample, args.limit, dry_run=args.dry_run, runs_dir=RUNS_DIR, models=models)
    print(f"\n{folder / 'sheet.html'}")
    if sys.platform == 'darwin' and not os.getenv('PROMPTLAB_NO_OPEN'):
        os.system(f"open '{folder / 'sheet.html'}'")


if __name__ == '__main__':
    main()
