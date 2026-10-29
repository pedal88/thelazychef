"""Amounts and temperatures in the reader's measuring system (services/measures.py)."""
import os
import sys
import unittest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.measures import degrees, fmt_amount, frac, system_of, temp  # noqa: E402


class MetricTests(unittest.TestCase):
    def test_metric_units_are_shown_as_stored(self):
        self.assertEqual(frac(1.5), '1½')
        self.assertEqual(frac(0.25), '¼')
        self.assertEqual(fmt_amount(2, 'clove'), '2 cloves')
        self.assertEqual(fmt_amount(1, 'clove'), '1 clove')
        self.assertEqual(fmt_amount(1.02, 'clove'), '1 clove')  # one, as written
        self.assertEqual(fmt_amount(3, 'piece'), '3')
        self.assertEqual(fmt_amount(1.5, 'tbsp'), '1½ tbsp')
        self.assertEqual(fmt_amount(437, 'g'), '440 g')
        self.assertEqual(fmt_amount(2.5, 'dl'), '2½ dl')
        self.assertEqual(fmt_amount(None, 'g'), '')

    def test_us_units_become_metric(self):
        self.assertEqual(fmt_amount(1, 'cup'), '240 ml')
        self.assertEqual(fmt_amount(0.5, 'cup'), '120 ml')
        self.assertEqual(fmt_amount(14, 'oz'), '400 g')
        self.assertEqual(fmt_amount(1, 'lb'), '450 g')
        self.assertEqual(fmt_amount(2, 'fl_oz'), '60 ml')


class USTests(unittest.TestCase):
    def us(self, amount, unit):
        return fmt_amount(amount, unit, 'us')

    def test_weights_in_ounces_and_pounds(self):
        self.assertEqual(self.us(400, 'g'), '14 oz')
        self.assertEqual(self.us(50, 'g'), '1¾ oz')
        self.assertEqual(self.us(500, 'g'), '1 lb')
        self.assertEqual(self.us(1, 'kg'), '2¼ lb')
        self.assertEqual(self.us(3, 'g'), '3 g')  # under a quarter ounce: grams, not a fraction of nothing
        self.assertEqual(self.us(1, 'lb'), '1 lb')

    def test_volumes_in_spoons_and_cups(self):
        self.assertEqual(self.us(5, 'ml'), '1 tsp')
        self.assertEqual(self.us(10, 'ml'), '2 tsp')
        self.assertEqual(self.us(30, 'ml'), '2 tbsp')
        self.assertEqual(self.us(60, 'ml'), '¼ cup')
        self.assertEqual(self.us(0.8, 'dl'), '⅓ cup')
        self.assertEqual(self.us(1.2, 'dl'), '½ cup')
        self.assertEqual(self.us(2.5, 'dl'), '1 cup')
        self.assertEqual(self.us(5, 'dl'), '2 cups')
        self.assertEqual(self.us(1, 'l'), '4¼ cups')
        self.assertEqual(self.us(1.5, 'cup'), '1½ cups')

    def test_spoons_counts_and_pinches_stay(self):
        self.assertEqual(self.us(1.5, 'tbsp'), '1½ tbsp')
        self.assertEqual(self.us(2, 'tsp'), '2 tsp')
        self.assertEqual(self.us(3, 'clove'), '3 cloves')
        self.assertEqual(self.us(1, 'pinch'), '1 pinch')
        self.assertEqual(self.us(2, 'piece'), '2')
        self.assertEqual(self.us(2, None), '2')

    def test_a_length_in_inches(self):
        self.assertEqual(self.us(4, 'cm'), '1½ in')  # ginger
        self.assertEqual(self.us(2, 'cm'), '¾ in')
        self.assertEqual(self.us(0.3, 'cm'), '¼ in')  # never nothing
        self.assertEqual(fmt_amount(4, 'cm'), '4 cm')


class TemperatureTests(unittest.TestCase):
    def test_oven_temperatures_to_25_and_core_temperatures_to_5(self):
        self.assertEqual([degrees(c, 'us') for c in (175, 180, 200, 220, 250)], [350, 350, 400, 425, 475])
        self.assertEqual([degrees(c, 'us') for c in (60, 75)], [140, 165])
        self.assertEqual(degrees(200, 'metric'), 200)
        self.assertIsNone(degrees(None, 'us'))

    def test_temp_with_its_unit(self):
        self.assertEqual(temp(220), '220 °C')
        self.assertEqual(temp(220, 'us'), '425 °F')
        self.assertEqual(temp(None, 'us'), '')


class SystemTests(unittest.TestCase):
    def test_unknown_values_are_metric(self):
        self.assertEqual(system_of('us'), 'us')
        self.assertEqual(system_of('metric'), 'metric')
        self.assertEqual(system_of(None), 'metric')
        self.assertEqual(system_of('imperial'), 'metric')


if __name__ == '__main__':
    unittest.main()
