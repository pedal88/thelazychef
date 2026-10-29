"""The app's look lives in static/css/tokens.css; base.html points Tailwind's colour names at it.

Guards the one-file promise: every scale base.html uses must exist in tokens.css with all its steps,
and the pages must not bring back colours of their own."""
import os
import re
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
STEPS = (50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950)


def read(*path):
    with open(os.path.join(ROOT, *path), encoding='utf-8') as f:
        return f.read()


class StyleTokenTests(unittest.TestCase):
    def test_every_scale_tailwind_uses_is_in_the_tokens(self):
        base, tokens = read('templates', 'base.html'), read('static', 'css', 'tokens.css')
        scales = set(re.findall(r"scale\('(\w+)'\)", base))
        self.assertEqual(scales, {'neutral', 'accent', 'prep', 'serve', 'danger', 'warning'})
        for name in scales:
            for step in STEPS:
                self.assertRegex(tokens, rf'--{name}-{step}:\s*\d+ \d+ \d+;', f'{name}-{step}')
        for var in ('--paper', '--font-sans', '--font-serif', '--font-mono', '--icon-stroke'):
            self.assertIn(var + ':', tokens)

    def test_the_v2_pages_and_their_styles_use_tokens_only(self):
        for path in (('static', 'css', f) for f in ('recipe_v2.css', 'ready.css', 'cook.css', 'delta.css')):
            self.assertEqual(re.findall(r'#[0-9a-fA-F]{3,6}\b', read(*path)), [], os.path.join(*path))
        for name in ('recipe_v2_make.html', 'chefs.html'):
            self.assertEqual(re.findall(r'#[0-9a-fA-F]{6}\b', read('templates', name)), [], name)


class LookTrialTests(unittest.TestCase):
    """The style trial (static/css/themes.css): every look sets every step of the scales it changes."""

    def test_each_look_has_whole_scales_and_fonts(self):
        themes = read('static', 'css', 'themes.css')
        for look in 'cdef':
            block = re.search(r':root\[data-look="%s"\] \{(.*?)\n\}' % look, themes, re.S).group(1)
            for name in ('neutral', 'accent', 'prep', 'serve'):
                for step in STEPS:
                    self.assertRegex(block, rf'--{name}-{step}: \d+ \d+ \d+;', f'{look} {name}-{step}')
            for var in ('--font-sans', '--font-serif', '--paper', '--icon-stroke', '--color-cook'):
                self.assertIn(var + ':', block, look)
        # its fonts are loaded, from the one list base.html and the social slides read (routes/_shared.LOOK_FONTS)
        from routes._shared import LOOK_FONTS
        self.assertEqual(sorted(LOOK_FONTS), list('cdef'))
        self.assertTrue(all(fonts.startswith('family=') for fonts in LOOK_FONTS.values()))
        self.assertIn('LOOK_FONTS|tojson', read('templates', 'base.html'))


class IconTests(unittest.TestCase):
    def test_the_sprite_is_valid_and_has_every_icon_the_templates_use(self):
        import glob
        import xml.dom.minidom

        sprite = xml.dom.minidom.parse(os.path.join(ROOT, 'static', 'icons', 'icons.svg'))  # one bad comment breaks every icon
        have = {s.getAttribute('id')[2:] for s in sprite.getElementsByTagName('symbol')}
        used = set()
        for path in glob.glob(os.path.join(ROOT, 'templates', '**', '*.html'), recursive=True):
            used |= set(re.findall(r"icon\('([\w-]+)'", read(path)))
        self.assertTrue(used)
        self.assertEqual(used - have, set())


if __name__ == '__main__':
    unittest.main()
