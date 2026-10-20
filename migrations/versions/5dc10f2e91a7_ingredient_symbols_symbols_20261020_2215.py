"""ingredient symbols symbols-20261020-2215

New ingredient symbols from run symbols-20261020-2215, approved in review: 1
ingredients get the new image_url and image_prompt, and image_notes and
image_form with any changes from review. 0 rejected ones keep
their image and get their review changes. The images are in
gs://thelazychef-assets/pantry/symbols/symbols-20261020-2215/.

Downgrade restores the old image_url, image_notes and image_form. The old
image_prompt is not kept: it belonged to the retired image pipeline.

Made by scripts/ingredient_symbols.py promote.

Revision ID: 5dc10f2e91a7
Revises: 3a45e5c980a1
Create Date: 2026-10-20

"""
from alembic import op
import sqlalchemy as sa


revision = '5dc10f2e91a7'
down_revision = '3a45e5c980a1'
branch_labels = None
depends_on = None

# id: (food_id, new_url, new_prompt, (new_notes, new_form), old_url, (old_notes, old_form))
APPROVED = {744: ('000703',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261020-2215/000703-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only green peas: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of green peas with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show it whole and fresh, as '
       'bought.',
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
