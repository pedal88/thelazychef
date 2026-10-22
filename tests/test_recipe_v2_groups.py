"""Kitchen groups for the ingredient lists (services/recipe_v2/groups.py)."""
import os
import sys
import unittest
from types import SimpleNamespace

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.recipe_v2.groups import group_of, grouped  # noqa: E402


def pantry(main, sub=None):
    return SimpleNamespace(main_category=main, sub_category=sub)


class GroupTests(unittest.TestCase):
    def test_the_pantry_categories_fold_into_kitchen_groups(self):
        self.assertEqual(group_of(pantry('vegetables', 'root vegetables')), 'produce')
        self.assertEqual(group_of(pantry('spices and herbs', 'fresh herbs')), 'produce')  # fresh basil is greens
        self.assertEqual(group_of(pantry('spices and herbs', 'dried herbs')), 'spices')
        self.assertEqual(group_of(pantry('canned and preserved', 'canned vegetables')), 'dry')
        self.assertEqual(group_of(pantry('dairy and egg', 'butter and spreads')), 'dairy')
        self.assertEqual(group_of(pantry('something new')), 'other')
        self.assertEqual(group_of(None), 'other')  # not in the pantry
        self.assertEqual(group_of(pantry('fats and oils'), is_staple=True), 'staples')

    def test_groups_come_in_shop_order_and_keep_the_order_inside(self):
        items = [{'n': 1, 'group': 'staples'}, {'n': 2, 'group': 'dairy'}, {'n': 3, 'group': 'produce'}, {'n': 4, 'group': 'dairy'}]
        self.assertEqual([(g['key'], [i['n'] for i in g['items']]) for g in grouped(items)],
                         [('produce', [3]), ('dairy', [2, 4]), ('staples', [1])])


if __name__ == '__main__':
    unittest.main()
