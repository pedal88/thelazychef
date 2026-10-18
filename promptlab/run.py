"""Run a task: every sample x every variant combination, saved with a log.

A run folder holds run.json (what was run, with which prompt, model and git
commit, and what came back), the outputs, and sheet.html for comparing them.
Runs live outside the repo (PROMPTLAB_DIR, default ~/promptlab-runs) because
the repo is public and outputs can be large.
"""
import datetime
import json
import os
import subprocess
import time
from pathlib import Path

from promptlab.compose import Task, combinations, label
from promptlab.sheet import write_sheet

RUNS_DIR = Path(os.getenv('PROMPTLAB_DIR', Path.home() / 'promptlab-runs'))


def _git(*args) -> str:
    try:
        return subprocess.run(['git', *args], capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return ''


def _sample_id(sample: dict, index: int) -> str:
    return str(sample.get('id') or sample.get('name') or index)


def plan(task: Task, vary: dict[str, list[str]], sample_set: str, limit: int | None) -> list[dict]:
    samples = task.samples(sample_set)[:limit] if limit else task.samples(sample_set)
    cells = []
    for index, sample in enumerate(samples):
        for choice in combinations(task, vary):
            cells.append({
                'sample': _sample_id(sample, index),
                'variant': label(choice),
                'choice': choice,
                'prompt': task.compose(choice, sample),
            })
    return cells


def run(task: Task, vary: dict[str, list[str]], sample_set: str = 'default', limit: int | None = None,
        dry_run: bool = False, runs_dir: Path = RUNS_DIR, runner=None) -> Path:
    from services import ai_models

    model = getattr(ai_models, task.model)
    started = datetime.datetime.now()
    folder = runs_dir / f"{started:%Y%m%d-%H%M%S}-{task.name}{'-dry' if dry_run else ''}"
    (folder / 'outputs').mkdir(parents=True)

    record = {
        'task': task.name, 'kind': task.kind, 'model': model, 'model_constant': task.model,
        'vary': vary, 'sample_set': sample_set, 'limit': limit, 'dry_run': dry_run,
        'started': started.isoformat(timespec='seconds'),
        'git_commit': _git('rev-parse', '--short', 'HEAD'),
        'git_dirty': bool(_git('status', '--porcelain', '--', str(task.path))),
        'cells': plan(task, vary, sample_set, limit),
    }

    if runner is None and not dry_run:
        from promptlab.runners import RUNNERS
        runner = RUNNERS[task.kind]

    for i, cell in enumerate(record['cells']):
        cell['id'] = f'c{i}'
        if dry_run:
            continue
        for attempt in range(3):
            try:
                output, meta = runner(model, cell['prompt'])
                break
            except NotImplementedError:
                raise
            except Exception as e:  # noqa: BLE001 - logged in the run, then retried
                cell['error'] = str(e)
                time.sleep(2 * (attempt + 1))
        else:
            print(f"  {cell['id']} failed: {cell['error'][:120]}")
            continue
        cell.pop('error', None)
        cell['meta'] = meta
        if task.kind == 'image':
            name = f"outputs/{cell['id']}.png"
            (folder / name).write_bytes(output)
            cell['output'] = name
        else:
            cell['output'] = output
        print(f"  {cell['id']} {cell['sample']} [{cell['variant']}] {meta.get('seconds', '')}s")

    record['finished'] = datetime.datetime.now().isoformat(timespec='seconds')
    (folder / 'run.json').write_text(json.dumps(record, indent=2, ensure_ascii=False))
    write_sheet(folder, record)
    return folder


def merge_scores(folder: Path, scores_file: Path) -> int:
    """Copy scores exported from sheet.html into run.json. Returns how many cells got a score."""
    record = json.loads((folder / 'run.json').read_text())
    scores = json.loads(scores_file.read_text())
    count = 0
    for cell in record['cells']:
        if cell['id'] in scores:
            cell['score'] = scores[cell['id']]
            count += 1
    (folder / 'run.json').write_text(json.dumps(record, indent=2, ensure_ascii=False))
    write_sheet(folder, record)
    return count
