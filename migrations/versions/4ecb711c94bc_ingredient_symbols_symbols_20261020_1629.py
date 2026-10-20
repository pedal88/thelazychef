"""ingredient symbols symbols-20261020-1629

New ingredient symbols from run symbols-20261020-1629, approved in review: 3
ingredients get the new image_url and image_prompt, and image_notes and
image_form with any changes from review. 0 rejected ones keep
their image and get their review changes. The images are in
gs://thelazychef-assets/pantry/symbols/symbols-20261020-1629/.

Downgrade restores the old image_url, image_notes and image_form. The old
image_prompt is not kept: it belonged to the retired image pipeline.

Made by scripts/ingredient_symbols.py promote.

Revision ID: 4ecb711c94bc
Revises: 2f32e64f2058
Create Date: 2026-10-20

"""
from alembic import op
import sqlalchemy as sa


revision = '4ecb711c94bc'
down_revision = '2f32e64f2058'
branch_labels = None
depends_on = None

# id: (food_id, new_url, new_prompt, (new_notes, new_form), old_url, (old_notes, old_form))
APPROVED = {741: ('000700',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261020-1629/000700-v2.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only dark chocolate: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of dark chocolate with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one broken piece of '
       'a dark chocolate bar, nothing else. A cork bottle of liquid chocolate next to the bar: wrong item, and more '
       'than one thing.',
       ('A cork bottle of liquid chocolate next to the bar: wrong item, and more than one thing.',
        'Show one broken piece of a dark chocolate bar, nothing else.'),
       None,
       (None, None)),
 742: ('000701',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261020-1629/000701-v2.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only red wine vinegar: no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of red wine vinegar with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one '
       'glass bottle with a cork stopper and the vinegar visible. Looks like a jam jar with a screw lid, not vinegar.',
       ('Looks like a jam jar with a screw lid, not vinegar.',
        'Show one glass bottle with a cork stopper and the vinegar visible.'),
       None,
       (None, None)),
 743: ('000702',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261020-1629/000702-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only vanilla sugar: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of vanilla sugar with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small paper bag, '
       'open at the top, with the contents visible.',
       (None, None),
       None,
       (None, None))}

# id: (food_id, (new_notes, new_form), (old_notes, old_form)) for rejected ones changed in review
REVIEWED = {}

SET_IMAGE = ("UPDATE ingredient SET image_url = :u, image_prompt = :p, image_notes = :n, image_form = :m, "
             "has_transparent_image = false WHERE id = :i AND food_id = :f")
SET_TEXT = "UPDATE ingredient SET image_notes = :n, image_form = :m WHERE id = :i AND food_id = :f"
RESTORE_IMAGE = ("UPDATE ingredient SET image_url = :u, image_prompt = NULL, image_notes = :n, image_form = :m "
                 "WHERE id = :i AND food_id = :f")


def upgrade():
    conn = op.get_bind()
    for i, (food_id, url, prompt, (notes, form), _old_url, _old) in APPROVED.items():
        conn.execute(sa.text(SET_IMAGE), {'u': url, 'p': prompt, 'n': notes, 'm': form, 'i': i, 'f': food_id})
    for i, (food_id, (notes, form), _old) in REVIEWED.items():
        conn.execute(sa.text(SET_TEXT), {'n': notes, 'm': form, 'i': i, 'f': food_id})


def downgrade():
    conn = op.get_bind()
    for i, (food_id, _url, _prompt, _new, old_url, (notes, form)) in APPROVED.items():
        conn.execute(sa.text(RESTORE_IMAGE), {'u': old_url, 'n': notes, 'm': form, 'i': i, 'f': food_id})
    for i, (food_id, _new, (notes, form)) in REVIEWED.items():
        conn.execute(sa.text(SET_TEXT), {'n': notes, 'm': form, 'i': i, 'f': food_id})
