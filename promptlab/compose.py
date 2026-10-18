"""Load a task and build prompts from its layers.

A layer variant is either a Jinja template (<variant>.j2) rendered with the
sample's fields, or a lookup table (<variant>.toml) with a `by` field naming
the sample field to look up (or a list of fields, tried in order) and a
`[values]` table; `default` is used when no field has an entry. A table may
name an `override` field: when the sample has it, its text is used instead,
for ingredients that do not fit their category. Empty layers are skipped. The final prompt joins the
layers in the order task.toml lists them.
"""
import itertools
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from jinja2 import Environment, StrictUndefined

LAB_DIR = Path(__file__).resolve().parent.parent / 'data' / 'prompts' / 'lab'
DEFAULT_VARIANT = 'default'

_jinja = Environment(undefined=StrictUndefined, keep_trailing_newline=False)


@dataclass
class Task:
    name: str
    path: Path
    kind: str                       # "image" or "text"
    model: str                      # constant name in services/ai_models.py
    layers: list[str]
    joiner: str = ' '
    sample_sets: dict = field(default_factory=dict)

    def variants(self, layer: str) -> list[str]:
        files = sorted((self.path / layer).glob('*'))
        return [f.stem for f in files if f.suffix in ('.j2', '.toml')]

    def _layer_file(self, layer: str, variant: str) -> Path:
        for suffix in ('.j2', '.toml'):
            candidate = self.path / layer / f'{variant}{suffix}'
            if candidate.exists():
                return candidate
        raise FileNotFoundError(f"{self.name}: layer '{layer}' has no variant '{variant}' ({', '.join(self.variants(layer))})")

    def render_layer(self, layer: str, variant: str, sample: dict) -> str:
        file = self._layer_file(layer, variant)
        if file.suffix == '.j2':
            text = _jinja.from_string(file.read_text()).render(**sample)
        else:
            table = tomllib.loads(file.read_text())
            fields = table['by'] if isinstance(table['by'], list) else [table['by']]
            values = table.get('values', {})
            key = next((sample[f] for f in fields if sample.get(f) in values), None)
            text = values[key] if key is not None else table.get('default', '')
            if table.get('override') and sample.get(table['override']):
                text = sample[table['override']]
            text = _jinja.from_string(text).render(**sample) if text else ''
        return ' '.join(text.split())

    def compose(self, choice: dict[str, str], sample: dict) -> str:
        parts = [self.render_layer(layer, choice.get(layer, DEFAULT_VARIANT), sample) for layer in self.layers]
        return self.joiner.join(p for p in parts if p)

    def samples(self, set_name: str = 'default') -> list[dict]:
        try:
            return self.sample_sets[set_name]
        except KeyError:
            raise KeyError(f"{self.name}: no sample set '{set_name}' ({', '.join(self.sample_sets)})") from None


def load_task(name: str, lab_dir: Path = LAB_DIR) -> Task:
    path = lab_dir / name
    config = tomllib.loads((path / 'task.toml').read_text())
    samples = tomllib.loads((path / 'samples.toml').read_text()) if (path / 'samples.toml').exists() else {}
    return Task(
        name=name, path=path, kind=config['kind'], model=config['model'],
        layers=config['layers'], joiner=config.get('join', ' '),
        sample_sets={k: v for k, v in samples.items() if isinstance(v, list)},
    )


def combinations(task: Task, vary: dict[str, list[str]]) -> list[dict[str, str]]:
    """Every combination of the varied layers; other layers use 'default'."""
    for layer in vary:
        if layer not in task.layers:
            raise ValueError(f"{task.name} has no layer '{layer}' (layers: {', '.join(task.layers)})")
    layers = list(vary)
    return [dict(zip(layers, values)) for values in itertools.product(*(vary[l] for l in layers))] or [{}]


def label(choice: dict[str, str]) -> str:
    return ', '.join(f'{k}={v}' for k, v in choice.items()) or 'default'
