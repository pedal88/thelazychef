"""Check that the Gemini key works and every model in services/ai_models.py exists.

Text models get one tiny generate call, which also catches billing problems
(402) and retired models (404). Image models are only looked up in the model
list, so the check costs almost nothing.

    python scripts/debug/verify_setup.py
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from services import ai_models  # noqa: E402

TEXT_MODELS = ['GEMINI_TEXT', 'GEMINI_TEXT_FAST']
IMAGE_MODELS = ['IMAGEN', 'IMAGEN_FAST']

client = ai_models.gemini_client()
ok = True

for name in TEXT_MODELS:
    model = getattr(ai_models, name)
    try:
        client.models.generate_content(model=model, contents='Reply with OK.')
        print(f"OK       {name:<17} {model}")
    except Exception as e:
        ok = False
        print(f"FAILED   {name:<17} {model}: {e}")

available = {m.name.removeprefix('models/') for m in client.models.list()}
for name in IMAGE_MODELS:
    model = getattr(ai_models, name)
    found = model in available
    ok = ok and found
    print(f"{'OK' if found else 'MISSING':<8} {name:<17} {model}")

sys.exit(0 if ok else 1)
