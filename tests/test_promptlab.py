"""Prompt lab: layer composition, variant combinations, runs and scores.

Uses a throwaway task in a temp folder and a fake runner, so no model is
called.
"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault('GOOGLE_API_KEY', 'test-key')

from promptlab.compose import combinations, load_task  # noqa: E402
from promptlab.run import merge_scores, run  # noqa: E402

FILES = {
    'task.toml': 'kind = "text"\nmodel = "GEMINI_TEXT"\nlayers = ["style", "category", "item"]\njoin = " | "\n',
    'style/default.j2': 'A photo of {{ name }}.',
    'style/b.j2': '{# comment #}An icon of {{ name }}.',
    'category/default.toml': 'by = "cat"\ndefault = "Generic."\n[values]\n"spice" = "Small heap of {{ name }}."\n',
    'item/default.j2': '{% if notes %}{{ notes }}{% endif %}',
    'samples.toml': 'default = [\n  { name = "anise", cat = "spice", notes = "Star shaped." },\n'
                    '  { name = "milk", cat = "dairy", notes = "" },\n]\n',
}


class PromptLabTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.lab = Path(self.tmp.name) / 'lab'
        for name, text in FILES.items():
            path = self.lab / 'demo' / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
        self.task = load_task('demo', lab_dir=self.lab)
        self.runs = Path(self.tmp.name) / 'runs'

    def tearDown(self):
        self.tmp.cleanup()

    def test_layers_join_in_order_and_skip_empty(self):
        anise, milk = self.task.samples()
        self.assertEqual(self.task.compose({}, anise), 'A photo of anise. | Small heap of anise. | Star shaped.')
        self.assertEqual(self.task.compose({'style': 'b'}, milk), 'An icon of milk. | Generic.')

    def test_combinations_cover_every_variant(self):
        self.assertEqual(combinations(self.task, {}), [{}])
        self.assertEqual(combinations(self.task, {'style': ['default', 'b']}),
                         [{'style': 'default'}, {'style': 'b'}])
        with self.assertRaises(ValueError):
            combinations(self.task, {'nope': ['a']})

    def test_missing_variant_and_variable_fail_loudly(self):
        with self.assertRaises(FileNotFoundError):
            self.task.compose({'style': 'zzz'}, self.task.samples()[0])
        with self.assertRaises(Exception):
            self.task.compose({}, {'cat': 'spice'})  # no name

    def test_dry_run_writes_log_and_sheet_without_calling_a_model(self):
        folder = run(self.task, {'style': ['default', 'b']}, dry_run=True, runs_dir=self.runs)
        record = json.loads((folder / 'run.json').read_text())
        self.assertEqual(len(record['cells']), 4)
        self.assertTrue(all('output' not in c for c in record['cells']))
        self.assertIn('An icon of milk.', (folder / 'sheet.html').read_text())

    def test_run_saves_outputs_and_scores_merge(self):
        calls = []

        def fake(model, prompt):
            calls.append((model, prompt))
            return prompt.upper(), {'seconds': 0}

        folder = run(self.task, {'style': ['b']}, runs_dir=self.runs, runner=fake)
        record = json.loads((folder / 'run.json').read_text())
        self.assertEqual(len(calls), 2)
        self.assertEqual(record['model'], 'gemini-flash-latest')
        self.assertEqual(record['cells'][0]['output'], 'AN ICON OF ANISE. | SMALL HEAP OF ANISE. | STAR SHAPED.')

        scores = Path(self.tmp.name) / 'scores.json'
        scores.write_text(json.dumps({'c0': {'value': 4, 'best': True}}))
        self.assertEqual(merge_scores(folder, scores), 1)
        self.assertEqual(json.loads((folder / 'run.json').read_text())['cells'][0]['score'], {'value': 4, 'best': True})


if __name__ == '__main__':
    unittest.main()
