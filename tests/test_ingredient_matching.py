"""Fuzzy matching must prefer no match over a wrong match.

A miss creates a pending ingredient an admin can review; a wrong match
silently puts the wrong ingredient in a recipe. These cases come from the
production pantry (October 2026), where the old matcher sent "water" to
"canned tuna in water" and "garlic powder" to "garlic".
"""
import os
import sys
import unittest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault('GOOGLE_API_KEY', 'test-key')

import ai_engine  # noqa: E402

PANTRY = [
    'water', 'canned tuna in water', 'garlic', 'garlic powder', 'lemon', 'lemon juice',
    'olive', 'olive oil', 'salted butter', 'unsalted butter', 'tomatoes', 'chicken breast',
    'chicken stock', 'schmaltz (chicken fat)', 'canned peas', 'canned pears', 'parmesan',
    'chili flakes', 'greek yogurt', 'red onion', 'spring onions', 'cherries',
]


class FuzzyMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ai_engine.set_pantry_memory([{'n': name, 'i': f'id:{name}', 's': False} for name in PANTRY])

    def match(self, name):
        food_id = ai_engine.get_pantry_id(name)
        return food_id.removeprefix('id:') if food_id else None

    def test_matches_spelling_plural_and_word_order(self):
        cases = {
            'Tomato': 'tomatoes',
            'chicken breasts': 'chicken breast',
            'Chilli Flakes': 'chili flakes',
            'greek yoghurt': 'greek yogurt',
            'onion, red': 'red onion',
            'spring onion': 'spring onions',
            'cherry': 'cherries',
            'parmesean': 'parmesan',
            'garlic, minced': 'garlic',
        }
        for name, expected in cases.items():
            with self.subTest(name=name):
                self.assertEqual(self.match(name), expected)

    def test_extra_or_different_words_do_not_match(self):
        cases = [
            'sparkling water',      # not water, not tuna
            'onion powder',         # not onion anything
            'lime juice',           # not lemon juice
            'butter',               # ambiguous: salted or unsalted
            'beef stock',           # not chicken stock
            'chicken fat',          # not schmaltz, not chicken stock
            'canned corn',          # not peas or pears
            'olive tapenade',
        ]
        for name in cases:
            with self.subTest(name=name):
                self.assertIsNone(self.match(name))

    def test_exact_names_still_win(self):
        self.assertEqual(self.match('water'), 'water')
        self.assertEqual(self.match('Garlic Powder'), 'garlic powder')
        self.assertEqual(self.match('lemon juice'), 'lemon juice')
        self.assertEqual(self.match('unsalted butter'), 'unsalted butter')

    def test_old_false_positives_are_gone(self):
        self.assertNotEqual(self.match('tuna'), 'canned tuna in water')
        self.assertNotEqual(self.match('chicken'), 'chicken stock')
        self.assertNotEqual(self.match('pears'), 'canned pears')


if __name__ == '__main__':
    unittest.main()
