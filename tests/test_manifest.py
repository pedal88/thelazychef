"""The home-screen app's manifest points at icons that exist, at the sizes it says (it once did not)."""
import json
import os

from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


def test_manifest_icons_exist_at_their_sizes():
    with open(os.path.join(ROOT, 'static', 'manifest.json'), encoding='utf-8') as f:
        manifest = json.load(f)
    assert manifest['display'] == 'standalone'
    assert manifest['icons']
    for icon in manifest['icons']:
        with Image.open(os.path.join(ROOT, icon['src'].lstrip('/'))) as image:
            assert f'{image.width}x{image.height}' == icon['sizes']
