"""recipe language

recipe.language: the language a recipe's text is written in (ISO 639-1, 'en' or 'nb'),
see services/recipe_v2/language.py. New recipes get it when they are made.

Existing recipes are filled in from their text: the title, the step texts and the
ingredient lines as written. Common words of each language are counted, and the
column is only set when one language clearly wins; otherwise it stays empty.
Nothing else is changed. Downgrade drops the column.

Revision ID: c4e8a1f05b3d
Revises: 5dc10f2e91a7
Create Date: 2026-10-21

"""
import re

from alembic import op
import sqlalchemy as sa


revision = 'c4e8a1f05b3d'
down_revision = '5dc10f2e91a7'
branch_labels = None
depends_on = None

NB = {'og', 'med', 'i', 'på', 'til', 'av', 'som', 'det', 'den', 'er', 'eller', 'ha', 'tilsett', 'skjær', 'hakk',
      'stek', 'kok', 'rør', 'la', 'minutter', 'ovnen', 'pannen', 'kjelen', 'gryten', 'bolle', 'biter', 'server',
      'smør', 'løk', 'hvitløk', 'fløte', 'melk', 'ut', 'opp', 'inn', 'mens', 'litt', 'godt'}
EN = {'the', 'and', 'with', 'in', 'on', 'to', 'of', 'or', 'until', 'add', 'stir', 'cook', 'minutes', 'oven',
      'pan', 'pot', 'bowl', 'pieces', 'serve', 'butter', 'onion', 'garlic', 'cream', 'milk', 'into', 'while',
      'then', 'it', 'a', 'is'}


def guess(text):
    """'nb', 'en' or None. Words with æ, ø or å count for Norwegian."""
    words = re.findall(r'[a-zæøå]+', re.sub(r'\{[^}]*\}', ' ', text.lower()))
    nb = sum(1 for w in words if w in NB or re.search('[æøå]', w))
    en = sum(1 for w in words if w in EN)
    if nb >= 3 and nb >= 2 * en:
        return 'nb'
    if en >= 3 and en >= 2 * nb:
        return 'en'
    return None


def upgrade():
    with op.batch_alter_table('recipe', schema=None) as batch_op:
        batch_op.add_column(sa.Column('language', sa.String(length=8), nullable=True))

    conn = op.get_bind()
    texts = {rid: [title or ''] for rid, title in conn.execute(sa.text('SELECT id, title FROM recipe'))}
    for sql in ('SELECT recipe_id, text FROM recipe_step', 'SELECT recipe_id, name FROM recipe_line',
                'SELECT recipe_id, text FROM instruction'):
        for rid, text in conn.execute(sa.text(sql)):
            if rid in texts and text:
                texts[rid].append(text)
    found = [{'id': rid, 'language': lang} for rid, parts in texts.items() if (lang := guess(' '.join(parts)))]
    if found:
        conn.execute(sa.text('UPDATE recipe SET language = :language WHERE id = :id'), found)


def downgrade():
    with op.batch_alter_table('recipe', schema=None) as batch_op:
        batch_op.drop_column('language')
