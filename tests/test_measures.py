"""Amounts and temperatures in the reader's measuring system (services/measures.py)."""
import os
import sys
import unittest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.measures import (degrees, density, fmt_amount, fmt_total, frac, localize_text, missed, system_of,  # noqa: E402
                               temp, unconverted)


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


class FreeTextTests(unittest.TestCase):
    def us(self, text):
        return localize_text(text, 'us')

    def test_temperatures(self):
        self.assertEqual(self.us('Sett ovnen på 175 °C over- og undervarme.'), 'Sett ovnen på 350 °F over- og undervarme.')
        self.assertEqual(self.us('60–70 °C i kjernen'), '140–160 °F i kjernen')
        self.assertEqual(self.us('Heat to 200°C'), 'Heat to 400 °F')
        self.assertEqual(self.us('Bake at 350 °F'), 'Bake at 350 °F')
        self.assertEqual(localize_text('Bake at 350 °F', 'metric'), 'Bake at 175 °C')  # a US source, for a metric reader

    def test_lengths(self):
        self.assertEqual(self.us('biter på 3 cm'), 'biter på 1¼ in')
        self.assertEqual(self.us('staver på ca. 1 cm'), 'staver på ca. ½ in')
        self.assertEqual(self.us('skiver på 5 mm'), 'skiver på ¼ in')
        self.assertEqual(self.us('en form på 20 × 20 cm'), 'en form på 8 × 8 in')
        self.assertEqual(self.us('a 24 cm springform'), 'a 9 in springform')
        self.assertEqual(self.us('1–2 cm thick'), '½–¾ in thick')

    def test_amounts(self):
        self.assertEqual(self.us('Øs opp 2 dl av vannet'), 'Øs opp ¾ cup av vannet')
        self.assertEqual(self.us('1,5 dl melk og 400 g kjøtt'), '⅔ cup melk og 14 oz kjøtt')
        self.assertEqual(self.us('2–3 dl vann'), '¾–1¼ cups vann')
        self.assertEqual(self.us('500 gram mel'), '1 lb mel')
        self.assertEqual(self.us('2 liter vann'), '8⅓ cups vann')

    def test_fractions(self):
        self.assertEqual(self.us('Tilsett ½ dl vann'), 'Tilsett 3½ tbsp vann')
        self.assertEqual(self.us('Rør inn 1½ dl fløte'), 'Rør inn ⅔ cup fløte')
        self.assertEqual(self.us('Add 1 ½ dl milk'), 'Add ⅔ cup milk')
        self.assertEqual(self.us('Use 1/2 dl oil'), 'Use 3½ tbsp oil')
        self.assertEqual(self.us('Pour 1 1/2 l water'), 'Pour 6¼ cups water')
        self.assertEqual(self.us('skiver på ½ cm'), 'skiver på ¼ in')
        self.assertEqual(self.us('1/2 sitron'), '1/2 sitron')  # no unit, nothing to convert
        self.assertEqual(localize_text('Tilsett ½ dl vann'), 'Tilsett ½ dl vann')

    def test_missed_finds_metric_measures_left_as_written(self):
        self.assertEqual(missed('Tilsett et par dl vann'), ['par dl'])
        self.assertEqual(missed('Kok opp en halv liter vann'), ['halv liter'])
        self.assertEqual(missed('Sett ovnen på to hundre °C'), ['hundre °C'])
        for text in ('Sett ovnen på 200 °C og hell i 1½ dl', 'Del {i3} i 4', 'G-streng', 'Kok i 10 min', '', None):
            self.assertEqual(missed(text), [], text)

    def test_what_is_left_alone(self):
        for text in ('Kok i 10 min', 'Snu 2 ganger', 'Tilsett {i3} og {i4}', 'Kok 5–6 minutter', '', None):
            self.assertEqual(self.us(text), text)
        self.assertEqual(localize_text('Sett ovnen på 200 °C, 3 cm, 2 dl'), 'Sett ovnen på 200 °C, 3 cm, 2 dl')

    def test_unconverted_finds_us_measures(self):
        self.assertEqual(unconverted('Add 2 cups flour, bake at 350°F in a 9" pan, or 200°'), ['2 cups', '350°F', '9"', '200°'])
        self.assertEqual(unconverted('Sett ovnen på 200 °C og hell i 2 dl'), [])
        self.assertEqual(unconverted(None), [])


class Pantry:
    def __init__(self, name, sub_category=None):
        self.name, self.sub_category = name, sub_category


class VolumeTests(unittest.TestCase):
    def test_what_us_recipes_measure_by_volume(self):
        self.assertEqual(density(Pantry('all-purpose flour')), 0.5)
        self.assertEqual(density(Pantry('brown sugar')), 0.89)
        self.assertEqual(density(Pantry('unsalted butter')), 0.95)
        self.assertEqual(density(Pantry('peanut butter')), 1.07)
        self.assertEqual(density(Pantry('ground cumin', 'ground spices')), 0.5)
        for name in ('sugar snap peas', 'flour tortillas', 'rice noodles', 'spaghetti', 'chicken thigh'):
            self.assertIsNone(density(Pantry(name)), name)
        self.assertIsNone(density(None))

    def test_a_weight_becomes_cups_and_spoons(self):
        us = lambda g, name, sub=None: fmt_amount(g, 'g', 'us', density(Pantry(name, sub)))  # noqa: E731
        self.assertEqual(us(250, 'all-purpose flour'), '2 cups')
        self.assertEqual(us(200, 'white sugar'), '1 cup')
        self.assertEqual(us(30, 'unsalted butter'), '2 tbsp')
        self.assertEqual(us(2, 'ground cumin', 'ground spices'), '¾ tsp')
        self.assertEqual(us(0.05, 'saffron', 'ground spices'), '1 pinch')
        self.assertEqual(us(400, 'spaghetti'), '14 oz')
        self.assertEqual(fmt_amount(250, 'g', 'metric', 0.5), '250 g')  # metric keeps the weight


class TotalTests(unittest.TestCase):
    def a(self, *pairs):
        return [{'amount': n, 'unit': u} for n, u in pairs]

    def test_one_sum_per_kind(self):
        self.assertEqual(fmt_total(self.a((1, 'dl'), (2, 'tbsp'))), '1⅓ dl')  # in the unit with the largest share
        self.assertEqual(fmt_total(self.a((1, 'dl'), (2, 'tbsp')), 'us'), '½ cup')
        self.assertEqual(fmt_total(self.a((1, 'cup'), (1, 'dl'))), '340 ml')  # a US unit's share in ml
        self.assertEqual(fmt_total(self.a((300, 'g'), (1, 'kg')), 'us'), '2¾ lb')
        self.assertEqual(fmt_total(self.a((200, 'g'), (1, 'dl')), 'us', 0.5), '2 cups')  # flour weighed and measured

    def test_kinds_and_single_amounts_stay_apart(self):
        self.assertEqual(fmt_total(self.a((2, 'clove'), (10, 'g'))), '2 cloves + 10 g')
        self.assertEqual(fmt_total(self.a((1.5, 'tbsp'),)), '1½ tbsp')
        self.assertEqual(fmt_total(self.a((400, 'g'),), 'us'), '14 oz')
        self.assertEqual(fmt_total([]), '')


class SystemTests(unittest.TestCase):
    def test_unknown_values_are_metric(self):
        self.assertEqual(system_of('us'), 'us')
        self.assertEqual(system_of('metric'), 'metric')
        self.assertEqual(system_of(None), 'metric')
        self.assertEqual(system_of('imperial'), 'metric')


if __name__ == '__main__':
    unittest.main()
