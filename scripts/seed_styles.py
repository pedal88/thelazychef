import sys
import os

# Add the project root to the python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
from database.models import db, VisualStyleGuide
from services.visual_orchestrator_service import VisualOrchestrator

STYLES = [
    {
        "scope": "ingredient",
        "base_wrapper": "A minimalist 3D isometric icon of {name}, isolated on a pure white background, soft studio lighting, ultra-detailed, 8k resolution.",
        "negative_prompt": "shadows, text, watermark, blurry, table, background elements, bowl, plate, person",
        "remove_background": True
    },
    {
        "scope": "taxonomy",
        "base_wrapper": "A conceptual 3D isometric icon representing {name}, isolated on a pure white background, soft studio lighting, ultra-detailed, pastel aesthetic.",
        "negative_prompt": "shadows, text, watermark, messy, distracting background",
        "remove_background": True
    },
    {
        "scope": "recipe_hero",
        "base_wrapper": "Top-down professional culinary food photography of {name}, sitting on a rustic wooden table, shallow depth of field, warm natural lighting, highly appetizing, global illumination.",
        "negative_prompt": "people, hands, text, cartoon, drawing, illustration, plastic, fake, unappetizing",
        "remove_background": False
    },
    {
        "scope": "tiktok_theme",
        "base_wrapper": "Cinematic wide-angle shot featuring {name}, vibrant punchy colors, aesthetic atmosphere, trending TikTok aesthetic, neon accents, dramatic rim lighting.",
        "negative_prompt": "boring, dull, plain, text, watermark",
        "remove_background": False
    }
]

def seed_styles():
    with app.app_context():
        print("Seeding visual style definitions...")
        for sd in STYLES:
            guide = db.session.execute(
                db.select(VisualStyleGuide).filter_by(scope=sd["scope"])
            ).scalar()

            if not guide:
                print(f"Adding new scope: {sd['scope']}")
                guide = VisualStyleGuide(
                    scope=sd['scope'],
                    base_wrapper=sd['base_wrapper'],
                    negative_prompt=sd['negative_prompt'],
                    remove_background=sd['remove_background']
                )
                db.session.add(guide)
            else:
                print(f"Updating existing scope: {sd['scope']}")
                guide.base_wrapper = sd['base_wrapper']
                guide.negative_prompt = sd['negative_prompt']
                guide.remove_background = sd['remove_background']

        db.session.commit()
        print("Seeding complete.")

if __name__ == "__main__":
    seed_styles()
