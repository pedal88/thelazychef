"""The documentation Claude Code reads stays true to the code (CLAUDE.md files, docs/, the project skills).

Two cheap checks against the most common decay: a file named in the docs that no longer exists, and an environment
variable the app reads that .env.example does not list. docs/archive/ is history and not checked.
"""
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ([p for p in ROOT.rglob('CLAUDE.md') if 'venv' not in p.parts and 'node_modules' not in p.parts]
        + [ROOT / 'README.md', ROOT / 'docs' / 'OPERATIONS.md', ROOT / 'docs' / 'SERVICES_AND_COSTS.md',
           ROOT / 'docs' / 'README_TOP_COMMANDS.md']
        + list((ROOT / '.claude' / 'skills').glob('*/SKILL.md')))
FILE = re.compile(r'`([A-Za-z0-9_./-]+\.(?:py|md|json|html|css|js|mjs|yaml|toml|jinja2|txt|sh|svg))`')
SKIP_PARTS = {'venv', '.git', 'node_modules', '__pycache__'}
# Read by the platform, not set by us: Cloud Run sets K_SERVICE
NOT_IN_ENV_EXAMPLE = {'K_SERVICE'}
APP_CODE = ['app.py', 'ai_engine.py', 'database', 'routes', 'services', 'utils', 'schemas', 'promptlab']


def _all_files():
    return [p for p in ROOT.rglob('*') if p.is_file() and not SKIP_PARTS & set(p.parts)]


def test_files_named_in_the_docs_exist():
    names = {p.name for p in _all_files()}
    missing = []
    for doc in DOCS:
        for ref in FILE.findall(doc.read_text(encoding='utf-8')):
            here = [ROOT / ref, doc.parent / ref]
            # A bare file name (`recipe_v2_make.html`) may live anywhere in the repo
            if not any(p.exists() for p in here) and not ('/' not in ref and ref in names):
                missing.append(f'{doc.relative_to(ROOT)}: {ref}')
    assert not missing, 'Files named in the docs that do not exist:\n' + '\n'.join(missing)


def test_env_example_lists_every_variable_the_app_reads():
    read = set()
    pattern = re.compile(r'''os\.(?:getenv|environ\.get|environ\.setdefault)\(\s*['"]([A-Z0-9_]+)['"]|os\.environ\[\s*['"]([A-Z0-9_]+)['"]''')
    for part in APP_CODE:
        path = ROOT / part
        for f in ([path] if path.is_file() else path.rglob('*.py')):
            for a, b in pattern.findall(f.read_text(encoding='utf-8')):
                read.add(a or b)
    listed = set(re.findall(r'^#?\s*([A-Z0-9_]+)=', (ROOT / '.env.example').read_text(encoding='utf-8'), re.M))
    missing = sorted(read - listed - NOT_IN_ENV_EXAMPLE)
    assert not missing, f'Read by the app but not in .env.example (and docs/SERVICES_AND_COSTS.md): {missing}'


def test_the_archive_is_marked_as_history():
    assert (ROOT / 'docs' / 'archive' / 'README.md').exists()
    for doc in DOCS:
        text = doc.read_text(encoding='utf-8')
        for name in os.listdir(ROOT / 'docs' / 'archive'):
            if name != 'README.md':
                assert f'docs/{name}' not in text, f'{doc.relative_to(ROOT)} points at the archived docs/{name}'
