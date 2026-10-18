"""ingredient symbols symbols-20261018-1900

New ingredient symbols from run symbols-20261018-1900, approved in review: 654
ingredients get the new image_url and image_prompt, and image_notes and
image_form with any changes from review. 0 rejected ones keep
their image and get their review changes. The images are in
gs://thelazychef-assets/pantry/symbols/symbols-20261018-1900/.

Downgrade restores the old image_url, image_notes and image_form. The old
image_prompt is not kept: it belonged to the retired image pipeline.

Made by scripts/ingredient_symbols.py promote.

Revision ID: 4f5dd927d78d
Revises: f713f4e4381f
Create Date: 2026-10-18

"""
from alembic import op
import sqlalchemy as sa


revision = '4f5dd927d78d'
down_revision = 'f713f4e4381f'
branch_labels = None
depends_on = None

# id: (food_id, new_url, new_prompt, (new_notes, new_form), old_url, (old_notes, old_form))
APPROVED = {1: ('000001',
     'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000001-v1.webp',
     'An ingredient symbol for a recipe app, recognizable at small sizes. Show only beef ribeye: no other foods, '
     'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
     'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
     'illustration of beef ribeye with subtle natural surface texture and soft shading, so the material reads clearly '
     '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show the raw, uncooked cut with '
     'its natural color.',
     (None, None),
     'https://storage.googleapis.com/thelazychef-assets/pantry/candidates/beef_ribeye_1773209474.png',
     (None, None)),
 2: ('000002',
     'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000002-v3.webp',
     'An ingredient symbol for a recipe app, recognizable at small sizes. Show only beef t-bone and porterhouse: no '
     'other foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), '
     'no colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
     'vector art illustration of beef t-bone and porterhouse with subtle natural surface texture and soft shading, so '
     'the material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show '
     'one single raw T-bone steak, with nothing else. Show one single raw T-bone steak, not two pieces.',
     ('Show one single raw T-bone steak, not two pieces.', 'Show one single raw T-bone steak, with nothing else.'),
     'https://storage.googleapis.com/thelazychef-assets/pantry/000002.png',
     (None, None)),
 3: ('000003',
     'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000003-v1.webp',
     'An ingredient symbol for a recipe app, recognizable at small sizes. Show only beef new york strip (striploin): '
     'no other foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background '
     '(#FFFFFF), no colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or '
     'numbers. A vector art illustration of beef new york strip (striploin) with subtle natural surface texture and '
     'soft shading, so the material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered '
     'framing. Show the raw, uncooked cut with its natural color.',
     (None, None),
     'https://storage.googleapis.com/thelazychef-assets/pantry/candidates/beef_new_york_strip_striploin_1773209471.png',
     (None, None)),
 4: ('000004',
     'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000004-v1.webp',
     'An ingredient symbol for a recipe app, recognizable at small sizes. Show only beef tenderloin/filet mignon: no '
     'other foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), '
     'no colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
     'vector art illustration of beef tenderloin/filet mignon with subtle natural surface texture and soft shading, so '
     'the material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show '
     'the raw, uncooked cut with its natural color.',
     (None, None),
     'https://storage.googleapis.com/thelazychef-assets/pantry/000004.png',
     (None, None)),
 5: ('000005',
     'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000005-v2.webp',
     'An ingredient symbol for a recipe app, recognizable at small sizes. Show only beef flank steak: no other foods, '
     'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
     'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
     'illustration of beef flank steak with subtle natural surface texture and soft shading, so the material reads '
     'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show the raw, uncooked cut '
     'with its natural color. Flank steak is a long, flat, thin cut with clearly visible lengthwise grain.',
     ('Flank steak is a long, flat, thin cut with clearly visible lengthwise grain.', None),
     'https://storage.googleapis.com/thelazychef-assets/pantry/candidates/beef_flank_steak_1773209467.png',
     (None, None)),
 6: ('000006',
     'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000006-v1.webp',
     'An ingredient symbol for a recipe app, recognizable at small sizes. Show only beef sirloin: no other foods, '
     'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
     'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
     'illustration of beef sirloin with subtle natural surface texture and soft shading, so the material reads clearly '
     '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show the raw, uncooked cut with '
     'its natural color.',
     (None, None),
     'https://storage.googleapis.com/thelazychef-assets/pantry/000006.png',
     (None, None)),
 7: ('000007',
     'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000007-v1.webp',
     'An ingredient symbol for a recipe app, recognizable at small sizes. Show only beef brisket: no other foods, '
     'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
     'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
     'illustration of beef brisket with subtle natural surface texture and soft shading, so the material reads clearly '
     '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show the raw, uncooked cut with '
     'its natural color.',
     (None, None),
     'https://storage.googleapis.com/thelazychef-assets/pantry/000007.png',
     (None, None)),
 8: ('000008',
     'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000008-v1.webp',
     'An ingredient symbol for a recipe app, recognizable at small sizes. Show only beef chuck roast/shoulder clod: no '
     'other foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), '
     'no colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
     'vector art illustration of beef chuck roast/shoulder clod with subtle natural surface texture and soft shading, '
     'so the material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show '
     'the raw, uncooked cut with its natural color.',
     (None, None),
     'https://storage.googleapis.com/thelazychef-assets/pantry/000008.png',
     (None, None)),
 9: ('000009',
     'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000009-v1.webp',
     'An ingredient symbol for a recipe app, recognizable at small sizes. Show only beef short ribs: no other foods, '
     'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
     'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
     'illustration of beef short ribs with subtle natural surface texture and soft shading, so the material reads '
     'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show the raw, uncooked cut '
     'with its natural color.',
     (None, None),
     'https://storage.googleapis.com/thelazychef-assets/pantry/000009.png',
     (None, None)),
 10: ('000010',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000010-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only beef round roast: no other foods, '
      'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
      'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
      'illustration of beef round roast with subtle natural surface texture and soft shading, so the material reads '
      'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show the raw, uncooked '
      'cut with its natural color.',
      (None, None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000010.png',
      (None, None)),
 11: ('000011',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000011-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only ground beef: no other foods, '
      'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
      'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
      'illustration of ground beef with subtle natural surface texture and soft shading, so the material reads clearly '
      '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show the raw, uncooked cut with '
      'its natural color. Lean minced beef, deep red with only small specks of fat.',
      ('Lean minced beef, deep red with only small specks of fat.', None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000011.png',
      ('Lean minced beef, deep red with only small specks of fat.', None)),
 12: ('000012',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000012-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only beef sausages: no other foods, '
      'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
      'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
      'illustration of beef sausages with subtle natural surface texture and soft shading, so the material reads '
      'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show the raw, uncooked '
      'cut with its natural color.',
      (None, None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000012.png',
      (None, None)),
 13: ('000013',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000013-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only goat shoulder: no other foods, '
      'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
      'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
      'illustration of goat shoulder with subtle natural surface texture and soft shading, so the material reads '
      'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show the raw, uncooked '
      'cut with its natural color.',
      (None, None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000013.png',
      (None, None)),
 14: ('000014',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000014-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only goat leg: no other foods, props, '
      'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
      'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
      'illustration of goat leg with subtle natural surface texture and soft shading, so the material reads clearly '
      '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show the raw, uncooked cut with '
      'its natural color.',
      (None, None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000014.png',
      (None, None)),
 15: ('000015',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000015-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only goat loin: no other foods, props, '
      'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
      'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
      'illustration of goat loin with subtle natural surface texture and soft shading, so the material reads clearly '
      '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show the raw, uncooked cut with '
      'its natural color.',
      (None, None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000015.png',
      (None, None)),
 16: ('000016',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000016-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only goat rack: no other foods, props, '
      'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
      'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
      'illustration of goat rack with subtle natural surface texture and soft shading, so the material reads clearly '
      '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show the raw, uncooked cut with '
      'its natural color.',
      (None, None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000016.png',
      (None, None)),
 17: ('000017',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000017-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only goat neck: no other foods, props, '
      'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
      'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
      'illustration of goat neck with subtle natural surface texture and soft shading, so the material reads clearly '
      '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show the raw, uncooked cut with '
      'its natural color.',
      (None, None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000017.png',
      (None, None)),
 18: ('000018',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000018-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only lamb chops: no other foods, '
      'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
      'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
      'illustration of lamb chops with subtle natural surface texture and soft shading, so the material reads clearly '
      '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show the raw, uncooked cut with '
      'its natural color.',
      (None, None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000018.png',
      (None, None)),
 19: ('000019',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000019-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only lamb sirloin: no other foods, '
      'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
      'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
      'illustration of lamb sirloin with subtle natural surface texture and soft shading, so the material reads '
      'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show the raw, uncooked '
      'cut with its natural color.',
      (None, None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000019.png',
      (None, None)),
 20: ('000020',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000020-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only lamb tenderloin: no other foods, '
      'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
      'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
      'illustration of lamb tenderloin with subtle natural surface texture and soft shading, so the material reads '
      'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show the raw, uncooked '
      'cut with its natural color.',
      (None, None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000020.png',
      (None, None)),
 21: ('000021',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000021-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only lamb rump: no other foods, props, '
      'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
      'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
      'illustration of lamb rump with subtle natural surface texture and soft shading, so the material reads clearly '
      '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show the raw, uncooked cut with '
      'its natural color.',
      (None, None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000021.png',
      (None, None)),
 22: ('000022',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000022-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only lamb shoulder slices: no other '
      'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
      'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
      'vector art illustration of lamb shoulder slices with subtle natural surface texture and soft shading, so the '
      'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show the '
      'raw, uncooked cut with its natural color.',
      (None, None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000022.png',
      (None, None)),
 23: ('000023',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000023-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only boneless lamb roast: no other '
      'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
      'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
      'vector art illustration of boneless lamb roast with subtle natural surface texture and soft shading, so the '
      'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show the '
      'raw, uncooked cut with its natural color.',
      (None, None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000023.png',
      (None, None)),
 24: ('000024',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000024-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only leg of lamb: no other foods, '
      'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
      'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
      'illustration of leg of lamb with subtle natural surface texture and soft shading, so the material reads clearly '
      '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show the raw, uncooked cut with '
      'its natural color.',
      (None, None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000024.png',
      (None, None)),
 25: ('000025',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000025-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only lamb ribs: no other foods, props, '
      'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
      'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
      'illustration of lamb ribs with subtle natural surface texture and soft shading, so the material reads clearly '
      '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show the raw, uncooked cut with '
      'its natural color.',
      (None, None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000025.png',
      (None, None)),
 26: ('000026',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000026-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only lamb shank: no other foods, '
      'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
      'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
      'illustration of lamb shank with subtle natural surface texture and soft shading, so the material reads clearly '
      '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show the raw, uncooked cut with '
      'its natural color.',
      (None, None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000026.png',
      (None, None)),
 27: ('000027',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000027-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only lamb for fårikål: no other foods, '
      'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
      'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
      'illustration of lamb for fårikål with subtle natural surface texture and soft shading, so the material reads '
      'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show the raw, uncooked '
      'cut with its natural color.',
      (None, None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000027.png',
      (None, None)),
 28: ('000028',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000028-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only ground lamb: no other foods, '
      'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
      'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
      'illustration of ground lamb with subtle natural surface texture and soft shading, so the material reads clearly '
      '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show the raw, uncooked cut with '
      'its natural color.',
      (None, None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000028.png',
      (None, None)),
 29: ('000029',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000029-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only lamb meat: no other foods, props, '
      'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
      'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
      'illustration of lamb meat with subtle natural surface texture and soft shading, so the material reads clearly '
      '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show the raw, uncooked cut with '
      'its natural color.',
      (None, None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000029.png',
      (None, None)),
 30: ('000030',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000030-v2.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only lamb dried ribs: no other foods, '
      'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
      'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
      'illustration of lamb dried ribs with subtle natural surface texture and soft shading, so the material reads '
      'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show the raw, uncooked '
      'cut with its natural color. Show one rack of dried, cured lamb ribs, not crossed sticks.',
      ('Show one rack of dried, cured lamb ribs, not crossed sticks.', None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000030.png',
      (None, None)),
 31: ('000031',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000031-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only lamb sausages: no other foods, '
      'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
      'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
      'illustration of lamb sausages with subtle natural surface texture and soft shading, so the material reads '
      'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show the raw, uncooked '
      'cut with its natural color.',
      (None, None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000031.png',
      (None, None)),
 32: ('000032',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000032-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only pork shoulder: no other foods, '
      'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
      'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
      'illustration of pork shoulder with subtle natural surface texture and soft shading, so the material reads '
      'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show the raw, uncooked '
      'cut with its natural color.',
      (None, None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000032.png',
      (None, None)),
 34: ('000034',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000034-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only rolled pork shoulder roast: no '
      'other foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background '
      '(#FFFFFF), no colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or '
      'numbers. A vector art illustration of rolled pork shoulder roast with subtle natural surface texture and soft '
      'shading, so the material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered '
      'framing. Show the raw, uncooked cut with its natural color.',
      (None, None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000034.png',
      (None, None)),
 35: ('000035',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000035-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only ground pork: no other foods, '
      'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
      'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
      'illustration of ground pork with subtle natural surface texture and soft shading, so the material reads clearly '
      '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show the raw, uncooked cut with '
      'its natural color.',
      (None, None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000035.png',
      (None, None)),
 36: ('000036',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000036-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only pork bone-in neck steaks: no '
      'other foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background '
      '(#FFFFFF), no colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or '
      'numbers. A vector art illustration of pork bone-in neck steaks with subtle natural surface texture and soft '
      'shading, so the material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered '
      'framing. Show the raw, uncooked cut with its natural color.',
      (None, None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000036.png',
      (None, None)),
 37: ('000037',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000037-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only pork loin: no other foods, props, '
      'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
      'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
      'illustration of pork loin with subtle natural surface texture and soft shading, so the material reads clearly '
      '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show the raw, uncooked cut with '
      'its natural color.',
      (None, None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000037.png',
      (None, None)),
 38: ('000038',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000038-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only pork filet mignon: no other '
      'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
      'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
      'vector art illustration of pork filet mignon with subtle natural surface texture and soft shading, so the '
      'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show the '
      'raw, uncooked cut with its natural color.',
      (None, None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000038.png',
      (None, None)),
 39: ('000039',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000039-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only pork sirloin: no other foods, '
      'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
      'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
      'illustration of pork sirloin with subtle natural surface texture and soft shading, so the material reads '
      'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show the raw, uncooked '
      'cut with its natural color.',
      (None, None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000039.png',
      (None, None)),
 41: ('000041',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000041-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only pork loin chops: no other foods, '
      'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
      'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
      'illustration of pork loin chops with subtle natural surface texture and soft shading, so the material reads '
      'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show the raw, uncooked '
      'cut with its natural color.',
      (None, None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000041.png',
      (None, None)),
 42: ('000042',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000042-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only pork smoked loin: no other foods, '
      'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
      'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
      'illustration of pork smoked loin with subtle natural surface texture and soft shading, so the material reads '
      'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show the raw, uncooked '
      'cut with its natural color.',
      (None, None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000042.png',
      (None, None)),
 43: ('000043',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000043-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only pork sausages: no other foods, '
      'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
      'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
      'illustration of pork sausages with subtle natural surface texture and soft shading, so the material reads '
      'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show the raw, uncooked '
      'cut with its natural color.',
      (None, None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000043.png',
      (None, None)),
 44: ('000044',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000044-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only chicken breast: no other foods, '
      'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
      'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
      'illustration of chicken breast with subtle natural surface texture and soft shading, so the material reads '
      'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show the raw, uncooked '
      'cut with its natural color. Pale pink raw chicken breast with visible natural muscle grain, clearly poultry, '
      'not salmon or pork.',
      ('Pale pink raw chicken breast with visible natural muscle grain, clearly poultry, not salmon or pork.', None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000044.png',
      ('Pale pink raw chicken breast with visible natural muscle grain, clearly poultry, not salmon or pork.', None)),
 45: ('000045',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000045-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only chicken drumstick: no other '
      'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
      'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
      'vector art illustration of chicken drumstick with subtle natural surface texture and soft shading, so the '
      'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show the '
      'raw, uncooked cut with its natural color.',
      (None, None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000045.png',
      (None, None)),
 46: ('000046',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000046-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only chicken fillet: no other foods, '
      'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
      'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
      'illustration of chicken fillet with subtle natural surface texture and soft shading, so the material reads '
      'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show the raw, uncooked '
      'cut with its natural color.',
      (None, None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000046.png',
      (None, None)),
 47: ('000047',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000047-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only chicken thigh: no other foods, '
      'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
      'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
      'illustration of chicken thigh with subtle natural surface texture and soft shading, so the material reads '
      'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show the raw, uncooked '
      'cut with its natural color.',
      (None, None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000047.png',
      (None, None)),
 48: ('000048',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000048-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only chicken wing: no other foods, '
      'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
      'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
      'illustration of chicken wing with subtle natural surface texture and soft shading, so the material reads '
      'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show the raw, uncooked '
      'cut with its natural color.',
      (None, None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000048.png',
      (None, None)),
 49: ('000049',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000049-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only chicken sausages: no other foods, '
      'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
      'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
      'illustration of chicken sausages with subtle natural surface texture and soft shading, so the material reads '
      'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show the raw, uncooked '
      'cut with its natural color.',
      (None, None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000049.png',
      (None, None)),
 50: ('000050',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000050-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only reindeer loin: no other foods, '
      'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
      'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
      'illustration of reindeer loin with subtle natural surface texture and soft shading, so the material reads '
      'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show the raw, uncooked '
      'cut with its natural color.',
      (None, None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000050.png',
      (None, None)),
 51: ('000051',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000051-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only reindeer tenderloin: no other '
      'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
      'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
      'vector art illustration of reindeer tenderloin with subtle natural surface texture and soft shading, so the '
      'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show the '
      'raw, uncooked cut with its natural color.',
      (None, None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000051.png',
      (None, None)),
 52: ('000052',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000052-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only reindeer leg roast: no other '
      'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
      'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
      'vector art illustration of reindeer leg roast with subtle natural surface texture and soft shading, so the '
      'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show the '
      'raw, uncooked cut with its natural color.',
      (None, None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000052.png',
      (None, None)),
 53: ('000053',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000053-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only reindeer leg steak: no other '
      'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
      'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
      'vector art illustration of reindeer leg steak with subtle natural surface texture and soft shading, so the '
      'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show the '
      'raw, uncooked cut with its natural color.',
      (None, None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000053.png',
      (None, None)),
 54: ('000054',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000054-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only reindeer shoulder: no other '
      'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
      'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
      'vector art illustration of reindeer shoulder with subtle natural surface texture and soft shading, so the '
      'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show the '
      'raw, uncooked cut with its natural color.',
      (None, None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000054.png',
      (None, None)),
 55: ('000055',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000055-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only reindeer ribs: no other foods, '
      'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
      'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
      'illustration of reindeer ribs with subtle natural surface texture and soft shading, so the material reads '
      'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show the raw, uncooked '
      'cut with its natural color.',
      (None, None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000055.png',
      (None, None)),
 56: ('000056',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000056-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only filet: no other foods, props, '
      'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
      'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
      'illustration of filet with subtle natural surface texture and soft shading, so the material reads clearly '
      '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show it raw, with its natural '
      'color.',
      (None, None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000056.png',
      (None, None)),
 57: ('000057',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000057-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only whole salmon: no other foods, '
      'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
      'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
      'illustration of whole salmon with subtle natural surface texture and soft shading, so the material reads '
      'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show it raw, with its '
      'natural color.',
      (None, None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000057.png',
      (None, None)),
 58: ('000058',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000058-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only shrimps: no other foods, props, '
      'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
      'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
      'illustration of shrimps with subtle natural surface texture and soft shading, so the material reads clearly '
      '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show it raw, with its natural '
      'color.',
      (None, None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000058.png',
      (None, None)),
 59: ('000059',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000059-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only scampi: no other foods, props, '
      'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
      'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
      'illustration of scampi with subtle natural surface texture and soft shading, so the material reads clearly '
      '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show it raw, with its natural '
      'color.',
      (None, None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000059.png',
      (None, None)),
 60: ('000060',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000060-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only lobster: no other foods, props, '
      'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
      'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
      'illustration of lobster with subtle natural surface texture and soft shading, so the material reads clearly '
      '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show it raw, with its natural '
      'color.',
      (None, None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000060.png',
      (None, None)),
 61: ('000061',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000061-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only chickpeas: no other foods, props, '
      'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
      'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
      'illustration of chickpeas with subtle natural surface texture and soft shading, so the material reads clearly '
      '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small heap of them.',
      (None, None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000061.png',
      (None, None)),
 62: ('000062',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000062-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only lentils: no other foods, props, '
      'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
      'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
      'illustration of lentils with subtle natural surface texture and soft shading, so the material reads clearly '
      '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small heap of them.',
      (None, None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000062.png',
      (None, None)),
 63: ('000063',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000063-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only black beans: no other foods, '
      'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
      'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
      'illustration of black beans with subtle natural surface texture and soft shading, so the material reads clearly '
      '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small heap of them.',
      (None, None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000063.png',
      (None, None)),
 64: ('000064',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000064-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only kidney beans: no other foods, '
      'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
      'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
      'illustration of kidney beans with subtle natural surface texture and soft shading, so the material reads '
      'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small heap of '
      'them.',
      (None, None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000064.png',
      (None, None)),
 65: ('000065',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000065-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only pinto beans: no other foods, '
      'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
      'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
      'illustration of pinto beans with subtle natural surface texture and soft shading, so the material reads clearly '
      '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small heap of them.',
      (None, None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000065.png',
      (None, None)),
 66: ('000066',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000066-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only split peas: no other foods, '
      'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
      'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
      'illustration of split peas with subtle natural surface texture and soft shading, so the material reads clearly '
      '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small heap of them.',
      (None, None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000066.png',
      (None, None)),
 67: ('000067',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000067-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only mung beans: no other foods, '
      'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
      'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
      'illustration of mung beans with subtle natural surface texture and soft shading, so the material reads clearly '
      '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small heap of them.',
      (None, None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000067.png',
      (None, None)),
 68: ('000068',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000068-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only edamame: no other foods, props, '
      'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
      'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
      'illustration of edamame with subtle natural surface texture and soft shading, so the material reads clearly '
      '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small heap of them.',
      (None, None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000068.png',
      (None, None)),
 69: ('000069',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000069-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only carrots: no other foods, props, '
      'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
      'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
      'illustration of carrots with subtle natural surface texture and soft shading, so the material reads clearly '
      '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show it whole and fresh, as '
      'bought.',
      (None, None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000069.png',
      (None, None)),
 70: ('000070',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000070-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only potatoes: no other foods, props, '
      'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
      'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
      'illustration of potatoes with subtle natural surface texture and soft shading, so the material reads clearly '
      '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show it whole and fresh, as '
      'bought.',
      (None, None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000070.png',
      (None, None)),
 71: ('000071',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000071-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only sweet potatoes: no other foods, '
      'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
      'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
      'illustration of sweet potatoes with subtle natural surface texture and soft shading, so the material reads '
      'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show it whole and fresh, '
      'as bought.',
      (None, None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000071.png',
      (None, None)),
 72: ('000072',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000072-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only beets: no other foods, props, '
      'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
      'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
      'illustration of beets with subtle natural surface texture and soft shading, so the material reads clearly '
      '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show it whole and fresh, as '
      'bought.',
      (None, None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000072.png',
      (None, None)),
 73: ('000073',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000073-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only turnips: no other foods, props, '
      'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
      'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
      'illustration of turnips with subtle natural surface texture and soft shading, so the material reads clearly '
      '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show it whole and fresh, as '
      'bought.',
      (None, None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000073.png',
      (None, None)),
 74: ('000074',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000074-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only radishes: no other foods, props, '
      'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
      'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
      'illustration of radishes with subtle natural surface texture and soft shading, so the material reads clearly '
      '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show it whole and fresh, as '
      'bought.',
      (None, None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000074.png',
      (None, None)),
 75: ('000075',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000075-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only parsnips: no other foods, props, '
      'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
      'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
      'illustration of parsnips with subtle natural surface texture and soft shading, so the material reads clearly '
      '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show it whole and fresh, as '
      'bought.',
      (None, None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000075.png',
      (None, None)),
 76: ('000076',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000076-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only rutabaga: no other foods, props, '
      'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
      'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
      'illustration of rutabaga with subtle natural surface texture and soft shading, so the material reads clearly '
      '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show it whole and fresh, as '
      'bought.',
      (None, None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000076.png',
      (None, None)),
 77: ('000077',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000077-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only spinach: no other foods, props, '
      'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
      'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
      'illustration of spinach with subtle natural surface texture and soft shading, so the material reads clearly '
      '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one head or a small bunch.',
      (None, None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000077.png',
      (None, None)),
 78: ('000078',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000078-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only kale: no other foods, props, '
      'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
      'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
      'illustration of kale with subtle natural surface texture and soft shading, so the material reads clearly '
      '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one head or a small bunch.',
      (None, None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/candidates/kale_1773218003.png',
      (None, None)),
 79: ('000079',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000079-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only lettuce: no other foods, props, '
      'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
      'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
      'illustration of lettuce with subtle natural surface texture and soft shading, so the material reads clearly '
      '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one head or a small bunch.',
      (None, None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000079.png',
      (None, None)),
 80: ('000080',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000080-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only arugula: no other foods, props, '
      'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
      'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
      'illustration of arugula with subtle natural surface texture and soft shading, so the material reads clearly '
      '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one head or a small bunch.',
      (None, None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000080.png',
      (None, None)),
 81: ('000081',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000081-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only collard greens: no other foods, '
      'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
      'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
      'illustration of collard greens with subtle natural surface texture and soft shading, so the material reads '
      'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one head or a small '
      'bunch.',
      (None, None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000081.png',
      (None, None)),
 82: ('000082',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000082-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only swiss chard: no other foods, '
      'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
      'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
      'illustration of swiss chard with subtle natural surface texture and soft shading, so the material reads clearly '
      '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one head or a small bunch.',
      (None, None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000082.png',
      (None, None)),
 83: ('000083',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000083-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only mustard greens: no other foods, '
      'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
      'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
      'illustration of mustard greens with subtle natural surface texture and soft shading, so the material reads '
      'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one head or a small '
      'bunch.',
      (None, None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000083.png',
      (None, None)),
 84: ('000084',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000084-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only beet greens: no other foods, '
      'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
      'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
      'illustration of beet greens with subtle natural surface texture and soft shading, so the material reads clearly '
      '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one head or a small bunch.',
      (None, None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000084.png',
      (None, None)),
 85: ('000085',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000085-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only broccoli: no other foods, props, '
      'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
      'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
      'illustration of broccoli with subtle natural surface texture and soft shading, so the material reads clearly '
      '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show it whole and fresh, as '
      'bought.',
      (None, None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000085.png',
      (None, None)),
 86: ('000086',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000086-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only cauliflower: no other foods, '
      'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
      'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
      'illustration of cauliflower with subtle natural surface texture and soft shading, so the material reads clearly '
      '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show it whole and fresh, as '
      'bought.',
      (None, None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000086.png',
      (None, None)),
 87: ('000087',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000087-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only cabbage: no other foods, props, '
      'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
      'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
      'illustration of cabbage with subtle natural surface texture and soft shading, so the material reads clearly '
      '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show it whole and fresh, as '
      'bought.',
      (None, None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000087.png',
      (None, None)),
 88: ('000088',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000088-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only brussels sprouts: no other foods, '
      'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
      'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
      'illustration of brussels sprouts with subtle natural surface texture and soft shading, so the material reads '
      'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show it whole and fresh, '
      'as bought.',
      (None, None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000088.png',
      (None, None)),
 89: ('000089',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000089-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only bok choy: no other foods, props, '
      'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
      'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
      'illustration of bok choy with subtle natural surface texture and soft shading, so the material reads clearly '
      '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show it whole and fresh, as '
      'bought.',
      (None, None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000089.png',
      (None, None)),
 90: ('000092',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000092-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only radish: no other foods, props, '
      'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
      'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
      'illustration of radish with subtle natural surface texture and soft shading, so the material reads clearly '
      '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show it whole and fresh, as '
      'bought.',
      (None, None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000092.png',
      (None, None)),
 91: ('000093',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000093-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only tomatoes: no other foods, props, '
      'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
      'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
      'illustration of tomatoes with subtle natural surface texture and soft shading, so the material reads clearly '
      '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show it whole and fresh, as '
      'bought.',
      (None, None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000093.png',
      (None, None)),
 92: ('000095',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000095-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only eggplant: no other foods, props, '
      'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
      'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
      'illustration of eggplant with subtle natural surface texture and soft shading, so the material reads clearly '
      '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show it whole and fresh, as '
      'bought.',
      (None, None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000095.png',
      (None, None)),
 93: ('000096',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000096-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only bell peppers: no other foods, '
      'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
      'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
      'illustration of bell peppers with subtle natural surface texture and soft shading, so the material reads '
      'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show it whole and fresh, '
      'as bought.',
      (None, None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000096.png',
      (None, None)),
 94: ('000097',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000097-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only chili peppers: no other foods, '
      'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
      'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
      'illustration of chili peppers with subtle natural surface texture and soft shading, so the material reads '
      'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show it whole and fresh, '
      'as bought.',
      (None, None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000097.png',
      (None, None)),
 95: ('000098',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000098-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only paprika: no other foods, props, '
      'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
      'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
      'illustration of paprika with subtle natural surface texture and soft shading, so the material reads clearly '
      '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show it whole and fresh, as '
      'bought.',
      (None, None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000098.png',
      (None, None)),
 96: ('000099',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000099-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only zucchini: no other foods, props, '
      'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
      'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
      'illustration of zucchini with subtle natural surface texture and soft shading, so the material reads clearly '
      '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show it whole and fresh, as '
      'bought.',
      (None, None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000099.png',
      (None, None)),
 97: ('000100',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000100-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only butternut squash: no other foods, '
      'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
      'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
      'illustration of butternut squash with subtle natural surface texture and soft shading, so the material reads '
      'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show it whole and fresh, '
      'as bought.',
      (None, None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000100.png',
      (None, None)),
 98: ('000101',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000101-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only acorn squash: no other foods, '
      'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
      'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
      'illustration of acorn squash with subtle natural surface texture and soft shading, so the material reads '
      'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show it whole and fresh, '
      'as bought.',
      (None, None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000101.png',
      (None, None)),
 99: ('000102',
      'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000102-v1.webp',
      'An ingredient symbol for a recipe app, recognizable at small sizes. Show only pumpkin: no other foods, props, '
      'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
      'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
      'illustration of pumpkin with subtle natural surface texture and soft shading, so the material reads clearly '
      '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show it whole and fresh, as '
      'bought.',
      (None, None),
      'https://storage.googleapis.com/thelazychef-assets/pantry/000102.png',
      (None, None)),
 100: ('000103',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000103-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only yellow squash: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of yellow squash with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show it whole and fresh, '
       'as bought.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000103.png',
       (None, None)),
 101: ('000104',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000104-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only spaghetti squash: no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of spaghetti squash with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show it '
       'whole and fresh, as bought.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000104.png',
       (None, None)),
 102: ('000105',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000105-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only chayote: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of chayote with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show it whole and fresh, as '
       'bought.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000105.png',
       (None, None)),
 103: ('000106',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000106-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only green beans: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of green beans with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show it whole and fresh, '
       'as bought.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000106.png',
       (None, None)),
 104: ('000107',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000107-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only snow peas: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of snow peas with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show it whole and fresh, as '
       'bought.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000107.png',
       (None, None)),
 105: ('000108',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000108-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only sugar snap peas: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of sugar snap peas with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show it whole and fresh, '
       'as bought.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000108.png',
       (None, None)),
 106: ('000109',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000109-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only okra: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of okra with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show it whole and fresh, as '
       'bought.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000109.png',
       (None, None)),
 107: ('000111',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000111-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only onion: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of onion with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show it whole and fresh, as '
       'bought.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000111.png',
       (None, None)),
 108: ('000112',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000112-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only garlic: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of garlic with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show it whole and fresh, as '
       'bought. A whole garlic bulb with one loose clove.',
       ('A whole garlic bulb with one loose clove.', None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000112.png',
       ('A whole garlic bulb with one loose clove.', None)),
 109: ('000113',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000113-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only shallots: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of shallots with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show it whole and fresh, as '
       'bought.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000113.png',
       (None, None)),
 110: ('000114',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000114-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only leeks: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of leeks with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show it whole and fresh, as '
       'bought.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000114.png',
       (None, None)),
 111: ('000115',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000115-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only fennel bulbs: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of fennel bulbs with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show it whole and fresh, '
       'as bought.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000115.png',
       (None, None)),
 112: ('000116',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000116-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only spring onions: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of spring onions with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show it whole and fresh, '
       'as bought.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000116.png',
       (None, None)),
 113: ('000117',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000117-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only celery: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of celery with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show it whole and fresh, as '
       'bought.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000117.png',
       (None, None)),
 114: ('000118',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000118-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only asparagus: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of asparagus with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show it whole and fresh, as '
       'bought.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000118.png',
       (None, None)),
 115: ('000119',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000119-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only rhubarb: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of rhubarb with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show it whole and fresh, as '
       'bought.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000119.png',
       (None, None)),
 116: ('000121',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000121-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only button mushrooms: no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of button mushrooms with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show two '
       'or three whole ones.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000121.png',
       (None, None)),
 117: ('000122',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000122-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only cremini: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of cremini with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show two or three whole ones.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000122.png',
       (None, None)),
 118: ('000123',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000123-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only portabella: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of portabella with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show two or three whole ones.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000123.png',
       (None, None)),
 119: ('000124',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000124-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only shiitake: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of shiitake with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show two or three whole ones.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000124.png',
       (None, None)),
 120: ('000125',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000125-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only oyster mushrooms: no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of oyster mushrooms with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show two '
       'or three whole ones.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000125.png',
       (None, None)),
 121: ('000126',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000126-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only enoki: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of enoki with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show two or three whole ones.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000126.png',
       (None, None)),
 122: ('000127',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000127-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only maitake: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of maitake with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show two or three whole ones.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000127.png',
       (None, None)),
 123: ('000128',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000128-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only king oyster: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of king oyster with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show two or three whole '
       'ones.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000128.png',
       (None, None)),
 124: ('000129',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000129-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only orange: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of orange with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one whole fruit.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000129.png',
       (None, None)),
 125: ('000130',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000130-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only lemon: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of lemon with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one whole fruit.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000130.png',
       (None, None)),
 126: ('000131',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000131-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only lime: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of lime with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one whole fruit.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000131.png',
       (None, None)),
 127: ('000132',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000132-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only grapefruit: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of grapefruit with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one whole fruit.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000132.png',
       (None, None)),
 128: ('000133',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000133-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only mandarin: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of mandarin with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one whole fruit.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000133.png',
       (None, None)),
 129: ('000134',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000134-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only tangerine: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of tangerine with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one whole fruit.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000134.png',
       (None, None)),
 130: ('000135',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000135-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only clementine: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of clementine with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one whole fruit.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000135.png',
       (None, None)),
 131: ('000136',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000136-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only pomelo: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of pomelo with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one whole fruit.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000136.png',
       (None, None)),
 132: ('000137',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000137-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only strawberries: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of strawberries with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small cluster of '
       'the fresh berries.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000137.png',
       (None, None)),
 133: ('000138',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000138-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only blueberries: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of blueberries with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small cluster of '
       'the fresh berries.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000138.png',
       (None, None)),
 134: ('000139',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000139-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only raspberries: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of raspberries with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small cluster of '
       'the fresh berries.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000139.png',
       (None, None)),
 135: ('000140',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000140-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only blackberries: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of blackberries with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small cluster of '
       'the fresh berries.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000140.png',
       (None, None)),
 136: ('000141',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000141-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only cranberries: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of cranberries with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small cluster of '
       'the fresh berries.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000141.png',
       (None, None)),
 137: ('000142',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000142-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only gooseberries: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of gooseberries with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small cluster of '
       'the fresh berries.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000142.png',
       (None, None)),
 138: ('000143',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000143-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only mulberries: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of mulberries with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small cluster of the '
       'fresh berries.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000143.png',
       (None, None)),
 139: ('000144',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000144-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only elderberries: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of elderberries with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small cluster of '
       'the fresh berries.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000144.png',
       (None, None)),
 140: ('000145',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000145-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only peach: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of peach with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show it whole and fresh, as '
       'bought.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000145.png',
       (None, None)),
 141: ('000146',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000146-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only plum: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of plum with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show it whole and fresh, as '
       'bought.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000146.png',
       (None, None)),
 142: ('000147',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000147-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only cherry: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of cherry with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show it whole and fresh, as '
       'bought.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000147.png',
       (None, None)),
 143: ('000148',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000148-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only apricot: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of apricot with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show it whole and fresh, as '
       'bought.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/candidates/apricot_1773209448.png',
       (None, None)),
 144: ('000149',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000149-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only nectarine: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of nectarine with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show it whole and fresh, as '
       'bought.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000149.png',
       (None, None)),
 145: ('000151',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000151-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only lychee: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of lychee with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show it whole and fresh, as '
       'bought.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000151.png',
       (None, None)),
 146: ('000152',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000152-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only olive: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of olive with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show it whole and fresh, as '
       'bought.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000152.png',
       (None, None)),
 147: ('000153',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000153-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only apple: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of apple with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show it whole and fresh, as '
       'bought.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/candidates/apple_1773209444.png',
       (None, None)),
 148: ('000154',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000154-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only pear: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of pear with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show it whole and fresh, as '
       'bought.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000154.png',
       (None, None)),
 149: ('000155',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000155-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only quince: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of quince with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show it whole and fresh, as '
       'bought.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000155.png',
       (None, None)),
 150: ('000156',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000156-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only asian pear: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of asian pear with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show it whole and fresh, as '
       'bought.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/candidates/asian_pear_1773209451.png',
       (None, None)),
 151: ('000157',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000157-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only banana: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of banana with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show it whole and fresh, as '
       'bought. One whole unpeeled yellow banana.',
       ('One whole unpeeled yellow banana.', None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000157.png',
       ('One whole unpeeled yellow banana.', None)),
 152: ('000158',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000158-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only pineapple: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of pineapple with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show it whole and fresh, as '
       'bought.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000158.png',
       (None, None)),
 153: ('000159',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000159-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only papaya: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of papaya with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show it whole and fresh, as '
       'bought.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000159.png',
       (None, None)),
 154: ('000160',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000160-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only mango: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of mango with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show it whole and fresh, as '
       'bought.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000160.png',
       (None, None)),
 155: ('000161',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000161-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only passion fruit: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of passion fruit with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show it whole and fresh, '
       'as bought.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000161.png',
       (None, None)),
 156: ('000162',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000162-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only guava: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of guava with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show it whole and fresh, as '
       'bought.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000162.png',
       (None, None)),
 157: ('000163',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000163-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only star fruit: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of star fruit with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show it whole and fresh, as '
       'bought.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000163.png',
       (None, None)),
 158: ('000164',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000164-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only dragon fruit: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of dragon fruit with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show it whole and fresh, '
       'as bought.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000164.png',
       (None, None)),
 159: ('000165',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000165-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only watermelon: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of watermelon with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show it whole and fresh, as '
       'bought.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000165.png',
       (None, None)),
 160: ('000166',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000166-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only cantaloupe: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of cantaloupe with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show it whole and fresh, as '
       'bought.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000166.png',
       (None, None)),
 161: ('000167',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000167-v2.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only honeydew: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of honeydew with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show it whole and fresh, as '
       'bought.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000167.png',
       (None, None)),
 162: ('000168',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000168-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only canary melon: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of canary melon with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show it whole and fresh, '
       'as bought.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000168.png',
       (None, None)),
 163: ('000169',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000169-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only galia melon: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of galia melon with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show it whole and fresh, '
       'as bought.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000169.png',
       (None, None)),
 164: ('000170',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000170-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only red grapes: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of red grapes with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show it whole and fresh, as '
       'bought.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000170.png',
       (None, None)),
 165: ('000171',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000171-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only green grapes: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of green grapes with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show it whole and fresh, '
       'as bought.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000171.png',
       (None, None)),
 166: ('000172',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000172-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only concord grapes: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of concord grapes with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show it whole and fresh, '
       'as bought.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000172.png',
       (None, None)),
 167: ('000173',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000173-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only black grapes: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of black grapes with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show it whole and fresh, '
       'as bought.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000173.png',
       (None, None)),
 168: ('000174',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000174-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only raisins: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of raisins with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small heap of it.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000174.png',
       (None, None)),
 169: ('000175',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000175-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only dried apricots: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of dried apricots with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small heap of it.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000175.png',
       (None, None)),
 170: ('000176',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000176-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only dried figs: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of dried figs with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small heap of it.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000176.png',
       (None, None)),
 171: ('000177',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000177-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only dates: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of dates with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small heap of it.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000177.png',
       (None, None)),
 172: ('000178',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000178-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only prunes: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of prunes with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small heap of it.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000178.png',
       (None, None)),
 173: ('000179',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000179-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only dried cranberries: no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of dried cranberries with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a '
       'small heap of it.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000179.png',
       (None, None)),
 174: ('000180',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000180-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only dried mango: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of dried mango with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small heap of it.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000180.png',
       (None, None)),
 175: ('000181',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000181-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only dried pineapple: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of dried pineapple with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small heap of it.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000181.png',
       (None, None)),
 176: ('000182',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000182-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only whole milk: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of whole milk with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one simple glass bottle of '
       'it.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/candidates/whole_milk_1773209440.png',
       (None, None)),
 177: ('000183',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000183-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only lowfat milk: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of lowfat milk with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one simple glass '
       'bottle of it.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000183.png',
       (None, None)),
 178: ('000184',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000184-v2.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only nonfat milk: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of nonfat milk with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one simple glass '
       'bottle of it.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000184.png',
       (None, None)),
 179: ('000185',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000185-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only buttermilk: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of buttermilk with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one simple glass bottle of '
       'it.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000185.png',
       (None, None)),
 180: ('000186',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000186-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only goat milk: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of goat milk with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one simple glass bottle of '
       'it.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000186.png',
       (None, None)),
 181: ('000187',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000187-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only lactose-free milk: no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of lactose-free milk with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one '
       'simple glass bottle of it.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000187.png',
       (None, None)),
 182: ('000188',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000188-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only soy milk: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of soy milk with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one simple glass bottle of '
       'it.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000188.png',
       (None, None)),
 183: ('000189',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000189-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only almond milk: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of almond milk with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one simple glass '
       'bottle of it.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000189.png',
       (None, None)),
 184: ('000190',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000190-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only oat milk: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of oat milk with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one simple glass bottle of '
       'it.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000190.png',
       (None, None)),
 185: ('000191',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000191-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only coconut milk: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of coconut milk with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one simple glass '
       'bottle of it.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000191.png',
       (None, None)),
 186: ('000192',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000192-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only rice milk: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of rice milk with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one simple glass bottle of '
       'it.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000192.png',
       (None, None)),
 187: ('000193',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000193-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only cheddar: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of cheddar with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one wedge or block.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000193.png',
       (None, None)),
 188: ('000194',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000194-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only mozzarella: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of mozzarella with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one wedge or block.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000194.png',
       (None, None)),
 189: ('000195',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000195-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only swiss: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of swiss with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one wedge or block.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000195.png',
       (None, None)),
 190: ('000196',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000196-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only parmesan: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of parmesan with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one wedge or block. A wedge '
       'of hard aged cheese with rind.',
       ('A wedge of hard aged cheese with rind.', None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000196.png',
       ('A wedge of hard aged cheese with rind.', None)),
 191: ('000197',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000197-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only feta: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of feta with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one wedge or block.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000197.png',
       (None, None)),
 192: ('000198',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000198-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only ricotta: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of ricotta with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one wedge or block.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000198.png',
       (None, None)),
 193: ('000199',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000199-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only cottage cheese: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of cottage cheese with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one wedge or block.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000199.png',
       (None, None)),
 194: ('000200',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000200-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only blue cheese: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of blue cheese with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one wedge or block.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000200.png',
       (None, None)),
 195: ('000201',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000201-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only goat cheese: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of goat cheese with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one wedge or block.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000201.png',
       (None, None)),
 196: ('000202',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000202-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only provolone: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of provolone with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one wedge or block.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000202.png',
       (None, None)),
 197: ('000203',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000203-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only cream cheese: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of cream cheese with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one wedge or block.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000203.png',
       (None, None)),
 198: ('000204',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000204-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only jarlsberg: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of jarlsberg with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one wedge or block.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000204.png',
       (None, None)),
 199: ('000205',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000205-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only plain yogurt: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of plain yogurt with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass jar '
       'with the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000205.png',
       (None, None)),
 200: ('000206',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000206-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only greek yogurt: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of greek yogurt with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass jar '
       'with the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000206.png',
       (None, None)),
 201: ('000207',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000207-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only lowfat yogurt: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of lowfat yogurt with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass jar '
       'with the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000207.png',
       (None, None)),
 202: ('000208',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000208-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only flavored yogurt: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of flavored yogurt with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass jar '
       'with the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000208.png',
       (None, None)),
 203: ('000209',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000209-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only nonfat yogurt: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of nonfat yogurt with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass jar '
       'with the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000209.png',
       (None, None)),
 204: ('000210',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000210-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only turkish yoghurt: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of turkish yoghurt with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass jar '
       'with the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000210.png',
       (None, None)),
 205: ('000211',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000211-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only salted butter: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of salted butter with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show only the block, '
       'with nothing next to it.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000211.png',
       (None, None)),
 206: ('000212',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000212-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only unsalted butter: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of unsalted butter with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show only the block, '
       'with nothing next to it.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000212.png',
       (None, None)),
 207: ('000213',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000213-v2.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only ghee: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of ghee with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass jar with '
       'the golden ghee visible, with nothing next to it.',
       (None, 'Show one small glass jar with the golden ghee visible, with nothing next to it.'),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000213.png',
       (None, None)),
 208: ('000215',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000215-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only whipped butter: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of whipped butter with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show only the block, '
       'with nothing next to it.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000215.png',
       (None, None)),
 209: ('000217',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000217-v2.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only sesame butter: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of sesame butter with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass jar '
       'with the contents visible, with nothing next to it.',
       (None, 'Show one small glass jar with the contents visible, with nothing next to it.'),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000217.png',
       (None, None)),
 210: ('000218',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000218-v2.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only nut butters (e.g. almond): no '
       'other foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background '
       '(#FFFFFF), no colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or '
       'numbers. A vector art illustration of nut butters (e.g. almond) with subtle natural surface texture and soft '
       'shading, so the material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered '
       'framing. Show one small glass jar with the contents visible, with nothing next to it.',
       (None, 'Show one small glass jar with the contents visible, with nothing next to it.'),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000218.png',
       (None, None)),
 211: ('000219',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000219-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only heavy cream: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of heavy cream with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass jar '
       'with the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000219.png',
       (None, None)),
 212: ('000220',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000220-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only light cream: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of light cream with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass jar '
       'with the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000220.png',
       (None, None)),
 213: ('000221',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000221-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only half and half: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of half and half with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass jar '
       'with the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000221.png',
       (None, None)),
 214: ('000222',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000222-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only sour cream: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of sour cream with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass jar with '
       'the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000222.png',
       (None, None)),
 215: ('000223',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000223-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only crème fraîche: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of crème fraîche with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass jar '
       'with the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000223.png',
       (None, None)),
 216: ('000224',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000224-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only whipping cream: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of whipping cream with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass jar '
       'with the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000224.png',
       (None, None)),
 217: ('000225',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000225-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only eggs: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of eggs with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show the whole eggs. Two whole '
       'brown eggs, clearly oval, with clean, smooth, evenly colored shells and no spots.',
       ('Two whole brown eggs, clearly oval, with clean, smooth, evenly colored shells and no spots.', None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000225.png',
       ('Two whole brown eggs, clearly oval, with clean, smooth, evenly colored shells and no spots.', None)),
 218: ('000226',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000226-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only egg whites: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of egg whites with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show the whole eggs.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000226.png',
       (None, None)),
 219: ('000227',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000227-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only egg yolks: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of egg yolks with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show the whole eggs.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000227.png',
       (None, None)),
 220: ('000228',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000228-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only cashews: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of cashews with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small heap of them.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000228.png',
       (None, None)),
 221: ('000229',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000229-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only walnuts: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of walnuts with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small heap of them.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000229.png',
       (None, None)),
 222: ('000230',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000230-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only pistachios: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of pistachios with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small heap of them.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000230.png',
       (None, None)),
 223: ('000231',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000231-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only pecans: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of pecans with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small heap of them.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000231.png',
       (None, None)),
 224: ('000232',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000232-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only hazelnuts: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of hazelnuts with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small heap of them.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000232.png',
       (None, None)),
 225: ('000233',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000233-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only macadamia nuts: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of macadamia nuts with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small heap of '
       'them.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000233.png',
       (None, None)),
 226: ('000234',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000234-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only chia seeds: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of chia seeds with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small heap of them.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000234.png',
       (None, None)),
 227: ('000235',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000235-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only flax seeds: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of flax seeds with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small heap of them.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000235.png',
       (None, None)),
 228: ('000236',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000236-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only pumpkin seeds: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of pumpkin seeds with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small heap of '
       'them.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000236.png',
       (None, None)),
 229: ('000237',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000237-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only sunflower seeds: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of sunflower seeds with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small heap of '
       'them.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000237.png',
       (None, None)),
 230: ('000238',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000238-v2.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only sesame seeds: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of sesame seeds with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small heap of '
       'them.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000238.png',
       (None, None)),
 231: ('000239',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000239-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only hemp seeds: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of hemp seeds with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small heap of them.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000239.png',
       (None, None)),
 232: ('000240',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000240-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only poppy seeds: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of poppy seeds with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small heap of '
       'them.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000240.png',
       (None, None)),
 233: ('000243',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000243-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only mustard seeds: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of mustard seeds with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small heap of '
       'them.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000243.png',
       (None, None)),
 234: ('000244',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000244-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only basil: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of basil with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small bunch.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000244.png',
       (None, None)),
 235: ('000245',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000245-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only cilantro: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of cilantro with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small bunch.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000245.png',
       (None, None)),
 236: ('000246',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000246-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only parsley: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of parsley with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small bunch.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000246.png',
       (None, None)),
 237: ('000247',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000247-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only mint: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of mint with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small bunch.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000247.png',
       (None, None)),
 238: ('000248',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000248-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only chives: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of chives with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small bunch.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000248.png',
       (None, None)),
 239: ('000249',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000249-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only dill: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of dill with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small bunch.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000249.png',
       (None, None)),
 240: ('000250',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000250-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only thyme: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of thyme with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small bunch.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000250.png',
       (None, None)),
 241: ('000251',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000251-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only oregano: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of oregano with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small bunch.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000251.png',
       (None, None)),
 242: ('000252',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000252-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only rosemary: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of rosemary with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small bunch.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000252.png',
       (None, None)),
 243: ('000253',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000253-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only tarragon: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of tarragon with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small bunch.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000253.png',
       (None, None)),
 244: ('000254',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000254-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only sage: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of sage with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small bunch.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000254.png',
       (None, None)),
 245: ('000255',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000255-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only lemongrass: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of lemongrass with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small bunch.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000255.png',
       (None, None)),
 246: ('000256',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000256-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only dried basil: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of dried basil with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small heap of the '
       'dried leaves.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000256.png',
       (None, None)),
 247: ('000257',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000257-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only dried oregano: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of dried oregano with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small heap of the '
       'dried leaves.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000257.png',
       (None, None)),
 248: ('000258',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000258-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only dried thyme: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of dried thyme with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small heap of the '
       'dried leaves.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000258.png',
       (None, None)),
 249: ('000259',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000259-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only dried rosemary: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of dried rosemary with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small heap of the '
       'dried leaves.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000259.png',
       (None, None)),
 250: ('000260',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000260-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only dried parsley: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of dried parsley with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small heap of the '
       'dried leaves.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000260.png',
       (None, None)),
 251: ('000261',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000261-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only dried dill: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of dried dill with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small heap of the dried '
       'leaves.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000261.png',
       (None, None)),
 252: ('000262',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000262-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only dried tarragon: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of dried tarragon with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small heap of the '
       'dried leaves.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000262.png',
       (None, None)),
 253: ('000263',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000263-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only dried mint: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of dried mint with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small heap of the dried '
       'leaves.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000263.png',
       (None, None)),
 254: ('000264',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000264-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only black peppercorns: no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of black peppercorns with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a '
       'few whole pieces.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000264.png',
       (None, None)),
 255: ('000265',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000265-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only white peppercorns: no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of white peppercorns with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a '
       'few whole pieces.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000265.png',
       (None, None)),
 256: ('000266',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000266-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only green peppercorns: no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of green peppercorns with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a '
       'few whole pieces.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000266.png',
       (None, None)),
 257: ('000267',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000267-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only pink peppercorns: no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of pink peppercorns with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a '
       'few whole pieces.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000267.png',
       (None, None)),
 258: ('000268',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000268-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only coriander seeds: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of coriander seeds with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a few whole pieces.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000268.png',
       (None, None)),
 259: ('000269',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000269-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only cumin seeds: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of cumin seeds with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a few whole pieces.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000269.png',
       (None, None)),
 260: ('000270',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000270-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only fennel seeds: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of fennel seeds with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a few whole pieces.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000270.png',
       (None, None)),
 261: ('000271',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000271-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only mustard seeds (yellow): no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of mustard seeds (yellow) with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a '
       'few whole pieces.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000271.png',
       (None, None)),
 262: ('000272',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000272-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only mustard seeds (brown): no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of mustard seeds (brown) with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a '
       'few whole pieces.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000272.png',
       (None, None)),
 263: ('000273',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000273-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only cardamom pods (green): no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of cardamom pods (green) with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a '
       'few whole pieces.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000273.png',
       (None, None)),
 264: ('000274',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000274-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only cardamom pods (black): no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of cardamom pods (black) with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a '
       'few whole pieces.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000274.png',
       (None, None)),
 265: ('000275',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000275-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only cloves: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of cloves with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a few whole pieces.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000275.png',
       (None, None)),
 266: ('000276',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000276-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only cinnamon sticks: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of cinnamon sticks with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a few whole pieces.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000276.png',
       (None, None)),
 267: ('000277',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000277-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only cassia bark: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of cassia bark with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a few whole pieces.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000277.png',
       (None, None)),
 268: ('000278',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000278-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only ground cumin: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of ground cumin with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass '
       'spice jar with the spice visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000278.png',
       (None, None)),
 269: ('000279',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000279-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only ground coriander: no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of ground coriander with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one '
       'small glass spice jar with the spice visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000279.png',
       (None, None)),
 270: ('000280',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000280-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only ground turmeric: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of ground turmeric with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass '
       'spice jar with the spice visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000280.png',
       (None, None)),
 271: ('000281',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000281-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only ground cinnamon: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of ground cinnamon with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass '
       'spice jar with the spice visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000281.png',
       (None, None)),
 272: ('000282',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000282-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only ground ginger: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of ground ginger with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass '
       'spice jar with the spice visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000282.png',
       (None, None)),
 273: ('000283',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000283-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only ground nutmeg: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of ground nutmeg with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass '
       'spice jar with the spice visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000283.png',
       (None, None)),
 274: ('000284',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000284-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only ground cloves: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of ground cloves with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass '
       'spice jar with the spice visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000284.png',
       (None, None)),
 275: ('000285',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000285-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only ground black pepper: no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of ground black pepper with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one '
       'small glass spice jar with the spice visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000285.png',
       (None, None)),
 276: ('000286',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000286-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only ground white pepper: no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of ground white pepper with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one '
       'small glass spice jar with the spice visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000286.png',
       (None, None)),
 277: ('000287',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000287-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only ground cardamom: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of ground cardamom with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass '
       'spice jar with the spice visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000287.png',
       (None, None)),
 278: ('000288',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000288-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only ground fennel: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of ground fennel with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass '
       'spice jar with the spice visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000288.png',
       (None, None)),
 279: ('000289',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000289-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only ground mustard: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of ground mustard with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass '
       'spice jar with the spice visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000289.png',
       (None, None)),
 280: ('000290',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000290-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only ground paprika: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of ground paprika with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass '
       'spice jar with the spice visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000290.png',
       (None, None)),
 281: ('000291',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000291-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only smoked paprika: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of smoked paprika with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass '
       'spice jar with the spice visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000291.png',
       (None, None)),
 282: ('000292',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000292-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only table salt: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of table salt with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass spice jar '
       'with the salt visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000292.png',
       (None, None)),
 283: ('000293',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000293-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only kosher salt: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of kosher salt with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass '
       'spice jar with the salt visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000293.png',
       (None, None)),
 284: ('000294',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000294-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only sea salt: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of sea salt with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass spice jar '
       'with the salt visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000294.png',
       (None, None)),
 285: ('000295',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000295-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only himalayan pink salt: no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of himalayan pink salt with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one '
       'small glass spice jar with the salt visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000295.png',
       (None, None)),
 286: ('000296',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000296-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only smoked salt: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of smoked salt with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass '
       'spice jar with the salt visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000296.png',
       (None, None)),
 287: ('000297',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000297-v2.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only flake salt: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of flake salt with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass spice jar '
       'with the salt visible. should not show salt crystals and a spice jar',
       ('Show the flaky salt in a small glass spice jar only, with no loose crystals next to it.', None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000297.png',
       (None, None)),
 288: ('000298',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000298-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only rock salt: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of rock salt with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass spice jar '
       'with the salt visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000298.png',
       (None, None)),
 289: ('000299',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000299-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only garlic salt: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of garlic salt with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass '
       'spice jar with the salt visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000299.png',
       (None, None)),
 290: ('000300',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000300-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only onion salt: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of onion salt with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass spice jar '
       'with the salt visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000300.png',
       (None, None)),
 291: ('000301',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000301-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only iodized salt: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of iodized salt with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass '
       'spice jar with the salt visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000301.png',
       (None, None)),
 292: ('000302',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000302-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only brown rice: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of brown rice with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small paper bag, open at '
       'the top, with the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000302.png',
       (None, None)),
 293: ('000303',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000303-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only quinoa: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of quinoa with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small paper bag, open at '
       'the top, with the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000303.png',
       (None, None)),
 294: ('000304',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000304-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only oats: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of oats with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small paper bag, open at '
       'the top, with the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000304.png',
       (None, None)),
 295: ('000305',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000305-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only barley: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of barley with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small paper bag, open at '
       'the top, with the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000305.png',
       (None, None)),
 296: ('000306',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000306-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only millet: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of millet with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small paper bag, open at '
       'the top, with the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000306.png',
       (None, None)),
 297: ('000307',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000307-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only bulgur: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of bulgur with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small paper bag, open at '
       'the top, with the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000307.png',
       (None, None)),
 298: ('000308',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000308-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only buckwheat: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of buckwheat with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small paper bag, open at '
       'the top, with the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000308.png',
       (None, None)),
 299: ('000309',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000309-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only white rice: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of white rice with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small paper bag, open at '
       'the top, with the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000309.png',
       (None, None)),
 300: ('000311',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000311-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only semolina: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of semolina with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small paper bag, open at '
       'the top, with the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000311.png',
       (None, None)),
 301: ('000312',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000312-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only instant oats: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of instant oats with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small paper bag, '
       'open at the top, with the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000312.png',
       (None, None)),
 302: ('000314',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000314-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only cornmeal: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of cornmeal with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small paper bag, open at '
       'the top, with the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000314.png',
       (None, None)),
 303: ('000315',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000315-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only pearled barley: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of pearled barley with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small paper bag, '
       'open at the top, with the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000315.png',
       (None, None)),
 304: ('000316',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000316-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only cornflakes: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of cornflakes with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small paper bag, open at '
       'the top, with the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000316.png',
       (None, None)),
 305: ('000317',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000317-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only oatmeal: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of oatmeal with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small paper bag, open at '
       'the top, with the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000317.png',
       (None, None)),
 306: ('000318',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000318-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only granola: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of granola with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small paper bag, open at '
       'the top, with the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000318.png',
       (None, None)),
 307: ('000319',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000319-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only bran flakes: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of bran flakes with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small paper bag, '
       'open at the top, with the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000319.png',
       (None, None)),
 308: ('000320',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000320-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only muesli: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of muesli with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small paper bag, open at '
       'the top, with the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000320.png',
       (None, None)),
 309: ('000321',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000321-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only rice puffs: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of rice puffs with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small paper bag, open at '
       'the top, with the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000321.png',
       (None, None)),
 310: ('000322',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000322-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only spaghetti: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of spaghetti with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small handful of the dry '
       'pasta.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000322.png',
       (None, None)),
 311: ('000323',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000323-v2.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only penne: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of penne with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small handful of the dry '
       'pasta.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000323.png',
       (None, None)),
 312: ('000324',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000324-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only fusilli: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of fusilli with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small handful of the dry '
       'pasta.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000324.png',
       (None, None)),
 313: ('000325',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000325-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only macaroni: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of macaroni with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small handful of the dry '
       'pasta.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000325.png',
       (None, None)),
 314: ('000326',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000326-v2.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only rigatoni: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of rigatoni with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small handful of the dry '
       'pasta.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000326.png',
       (None, None)),
 315: ('000327',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000327-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only lasagna sheets: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of lasagna sheets with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small handful of '
       'the dry pasta.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000327.png',
       (None, None)),
 316: ('000328',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000328-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only egg noodles: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of egg noodles with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small bundle of '
       'the dry noodles.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000328.png',
       (None, None)),
 317: ('000329',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000329-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only ramen noodles: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of ramen noodles with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small bundle of '
       'the dry noodles.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000329.png',
       (None, None)),
 318: ('000330',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000330-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only rice noodles: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of rice noodles with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small bundle of '
       'the dry noodles.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000330.png',
       (None, None)),
 319: ('000331',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000331-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only white bread: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of white bread with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one whole loaf.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000331.png',
       (None, None)),
 320: ('000332',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000332-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only whole wheat bread: no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of whole wheat bread with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one '
       'whole loaf.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000332.png',
       (None, None)),
 321: ('000333',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000333-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only multigrain bread: no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of multigrain bread with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one '
       'whole loaf.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000333.png',
       (None, None)),
 322: ('000334',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000334-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only rye bread: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of rye bread with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one whole loaf.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000334.png',
       (None, None)),
 323: ('000335',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000335-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only sourdough: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of sourdough with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one whole loaf.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000335.png',
       (None, None)),
 324: ('000336',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000336-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only brioche: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of brioche with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one whole loaf.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000336.png',
       (None, None)),
 325: ('000337',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000337-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only ciabatta: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of ciabatta with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one whole loaf.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000337.png',
       (None, None)),
 326: ('000338',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000338-v2.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only pumpernickel: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of pumpernickel with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one whole loaf. '
       'just a black regular bread was generated',
       ('Pumpernickel is a dense, dark brown, rectangular rye loaf, not a round black bread.', None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000338.png',
       (None, None)),
 327: ('000339',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000339-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only tortilla: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of tortilla with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one whole flatbread.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000339.png',
       (None, None)),
 328: ('000340',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000340-v2.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only pita: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of pita with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one whole flatbread. Show '
       'one flat, round pita bread, not a bowl or a pie crust.',
       ('Show one flat, round pita bread, not a bowl or a pie crust.', None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000340.png',
       (None, None)),
 329: ('000341',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000341-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only naan: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of naan with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one whole flatbread.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000341.png',
       (None, None)),
 330: ('000342',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000342-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only roti: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of roti with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one whole flatbread.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000342.png',
       (None, None)),
 331: ('000343',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000343-v3.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only focaccia: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of focaccia with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one whole flatbread. '
       'Focaccia is a flat rectangular slab with deep dimples and a golden top, not round.',
       ('Focaccia is a flat rectangular slab with deep dimples and a golden top, not round.', None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000343.png',
       (None, None)),
 332: ('000344',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000344-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only croissant: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of croissant with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one piece.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000344.png',
       (None, None)),
 333: ('000345',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000345-v2.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only danish pastry: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of danish pastry with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one piece. there '
       'should not be blueberry on it',
       ('No berries or fruit on top.', None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000345.png',
       (None, None)),
 334: ('000346',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000346-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only puff pastry: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of puff pastry with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one piece.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000346.png',
       (None, None)),
 335: ('000347',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000347-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only cinnamon roll: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of cinnamon roll with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one piece.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000347.png',
       (None, None)),
 336: ('000348',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000348-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only all-purpose flour: no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of all-purpose flour with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a '
       'small paper bag, open at the top, with the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000348.png',
       (None, None)),
 337: ('000349',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000349-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only whole wheat flour: no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of whole wheat flour with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a '
       'small paper bag, open at the top, with the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000349.png',
       (None, None)),
 338: ('000350',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000350-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only spelt flour: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of spelt flour with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small paper bag, '
       'open at the top, with the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000350.png',
       (None, None)),
 339: ('000351',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000351-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only almond flour: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of almond flour with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small paper bag, '
       'open at the top, with the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000351.png',
       (None, None)),
 340: ('000352',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000352-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only rye flour: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of rye flour with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small paper bag, open at '
       'the top, with the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000352.png',
       (None, None)),
 341: ('000353',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000353-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only barley flour: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of barley flour with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small paper bag, '
       'open at the top, with the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000353.png',
       (None, None)),
 342: ('000354',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000354-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only buckwheat flour: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of buckwheat flour with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small paper bag, '
       'open at the top, with the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000354.png',
       (None, None)),
 343: ('000355',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000355-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only oat flour: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of oat flour with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small paper bag, open at '
       'the top, with the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000355.png',
       (None, None)),
 344: ('000356',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000356-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only corn flour: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of corn flour with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small paper bag, open at '
       'the top, with the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000356.png',
       (None, None)),
 345: ('000357',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000357-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only potato flour: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of potato flour with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small paper bag, '
       'open at the top, with the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000357.png',
       (None, None)),
 346: ('000358',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000358-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only white sugar: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of white sugar with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small paper bag, '
       'open at the top, with the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000358.png',
       (None, None)),
 347: ('000359',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000359-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only powdered sugar: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of powdered sugar with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small paper bag, '
       'open at the top, with the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000359.png',
       (None, None)),
 348: ('000360',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000360-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only brown sugar: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of brown sugar with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small paper bag, '
       'open at the top, with the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000360.png',
       (None, None)),
 349: ('000361',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000361-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only maple sugar: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of maple sugar with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small paper bag, '
       'open at the top, with the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000361.png',
       (None, None)),
 350: ('000362',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000362-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only glucose: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of glucose with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small paper bag, open at '
       'the top, with the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000362.png',
       (None, None)),
 351: ('000363',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000363-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only honey: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of honey with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass jar of '
       'honey with the honey visible, with nothing next to it.',
       (None, 'Show one small glass jar of honey with the honey visible, with nothing next to it.'),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000363.png',
       (None, None)),
 352: ('000364',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000364-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only baking powder: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of baking powder with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000364.png',
       (None, None)),
 353: ('000365',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000365-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only baking soda: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of baking soda with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000365.png',
       (None, None)),
 354: ('000366',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000366-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only active dry yeast: no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of active dry yeast with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000366.png',
       (None, None)),
 355: ('000367',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000367-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only instant yeast: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of instant yeast with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000367.png',
       (None, None)),
 356: ('000368',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000368-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only fresh yeast: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of fresh yeast with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000368.png',
       (None, None)),
 357: ('000369',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000369-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only sourdough starter: no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of sourdough starter with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000369.png',
       (None, None)),
 358: ('000371',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000371-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only almond extract: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of almond extract with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass '
       'bottle with a cork.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000371.png',
       (None, None)),
 359: ('000372',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000372-v2.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only lemon zest: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of lemon zest with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small heap of fresh lemon '
       'zest curls, with nothing else.',
       (None, 'Show a small heap of fresh lemon zest curls, with nothing else.'),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000372.png',
       (None, None)),
 360: ('000373',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000373-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only vanilla extract: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of vanilla extract with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass '
       'bottle with a cork.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000373.png',
       (None, None)),
 361: ('000374',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000374-v2.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only cinnamon: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of cinnamon with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show two cinnamon sticks, with '
       'nothing else.',
       (None, 'Show two cinnamon sticks, with nothing else.'),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000374.png',
       (None, None)),
 362: ('000375',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000375-v2.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only nutmeg: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of nutmeg with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show two whole nutmegs, one of '
       'them cut in half, with nothing else.',
       (None, 'Show two whole nutmegs, one of them cut in half, with nothing else.'),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000375.png',
       (None, None)),
 363: ('000376',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000376-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only cardamom: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of cardamom with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a few green cardamom pods, '
       'with nothing else.',
       (None, 'Show a few green cardamom pods, with nothing else.'),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000376.png',
       (None, None)),
 364: ('000377',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000377-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only cocoa powder: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of cocoa powder with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small heap of '
       'cocoa powder, with nothing else.',
       (None, 'Show a small heap of cocoa powder, with nothing else.'),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000377.png',
       (None, None)),
 365: ('000378',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000378-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only olive oil: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of olive oil with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one glass bottle with a '
       'cork stopper and the oil visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000378.png',
       (None, None)),
 366: ('000379',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000379-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only extra virgin olive oil: no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of extra virgin olive oil with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one '
       'glass bottle with a cork stopper and the oil visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000379.png',
       (None, None)),
 367: ('000380',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000380-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only canola oil: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of canola oil with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one glass bottle with a '
       'cork stopper and the oil visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000380.png',
       (None, None)),
 368: ('000381',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000381-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only sunflower oil: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of sunflower oil with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one glass bottle '
       'with a cork stopper and the oil visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000381.png',
       (None, None)),
 369: ('000382',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000382-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only soybean oil: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of soybean oil with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one glass bottle '
       'with a cork stopper and the oil visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000382.png',
       (None, None)),
 370: ('000383',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000383-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only grapeseed oil: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of grapeseed oil with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one glass bottle '
       'with a cork stopper and the oil visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000383.png',
       (None, None)),
 371: ('000384',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000384-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only butter: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of butter with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show only the block, with '
       'nothing next to it.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000384.png',
       (None, None)),
 373: ('000386',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000386-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only lard (pork fat): no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of lard (pork fat) with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show only the block, '
       'with nothing next to it.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000386.png',
       (None, None)),
 374: ('000387',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000387-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only tallow (beef fat): no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of tallow (beef fat) with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show only '
       'the block, with nothing next to it.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000387.png',
       (None, None)),
 375: ('000388',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000388-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only duck fat: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of duck fat with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show only the block, with '
       'nothing next to it.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000388.png',
       (None, None)),
 376: ('000389',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000389-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only chicken fat (schmaltz): no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of chicken fat (schmaltz) with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show only '
       'the block, with nothing next to it.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000389.png',
       (None, None)),
 377: ('000390',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000390-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only bacon fat: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of bacon fat with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show only the block, with '
       'nothing next to it.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000390.png',
       (None, None)),
 378: ('000391',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000391-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only coconut oil: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of coconut oil with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show only the block, '
       'with nothing next to it.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000391.png',
       (None, None)),
 379: ('000392',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000392-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only cocoa butter: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of cocoa butter with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show only the block, '
       'with nothing next to it.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000392.png',
       (None, None)),
 380: ('000393',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000393-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only palm oil: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of palm oil with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show only the block, with '
       'nothing next to it.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000393.png',
       (None, None)),
 381: ('000394',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000394-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only vegetable shortening: no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of vegetable shortening with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show only '
       'the block, with nothing next to it.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000394.png',
       (None, None)),
 382: ('000395',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000395-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only hydrogenated vegetable fat: no '
       'other foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background '
       '(#FFFFFF), no colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or '
       'numbers. A vector art illustration of hydrogenated vegetable fat with subtle natural surface texture and soft '
       'shading, so the material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered '
       'framing. Show only the block, with nothing next to it.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000395.png',
       (None, None)),
 383: ('000396',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000396-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only truffle oil: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of truffle oil with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one glass bottle '
       'with a cork stopper and the oil visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000396.png',
       (None, None)),
 384: ('000397',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000397-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only sesame oil: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of sesame oil with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one glass bottle with a '
       'cork stopper and the oil visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000397.png',
       (None, None)),
 385: ('000398',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000398-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only chili oil: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of chili oil with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one glass bottle with a '
       'cork stopper and the oil visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000398.png',
       (None, None)),
 386: ('000399',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000399-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only garlic-infused oil: no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of garlic-infused oil with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one '
       'glass bottle with a cork stopper and the oil visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000399.png',
       (None, None)),
 387: ('000400',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000400-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only basil-infused oil: no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of basil-infused oil with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one '
       'glass bottle with a cork stopper and the oil visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000400.png',
       (None, None)),
 388: ('000401',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000401-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only lemon-infused olive oil: no '
       'other foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background '
       '(#FFFFFF), no colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or '
       'numbers. A vector art illustration of lemon-infused olive oil with subtle natural surface texture and soft '
       'shading, so the material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered '
       'framing. Show one glass bottle with a cork stopper and the oil visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000401.png',
       (None, None)),
 389: ('000402',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000402-v3.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only walnut oil: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of walnut oil with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one glass bottle with a '
       'cork stopper and the oil visible. No text or letters on the bottle. Only the oil in the bottle, no walnuts '
       'inside or next to it.',
       ('No text or letters on the bottle. Only the oil in the bottle, no walnuts inside or next to it.', None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000402.png',
       (None, None)),
 390: ('000403',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000403-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only pumpkin seed oil: no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of pumpkin seed oil with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one '
       'glass bottle with a cork stopper and the oil visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000403.png',
       (None, None)),
 391: ('000404',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000404-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only hemp seed oil: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of hemp seed oil with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one glass bottle '
       'with a cork stopper and the oil visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000404.png',
       (None, None)),
 392: ('000405',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000405-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only margarine: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of margarine with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass jar with '
       'the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000405.png',
       (None, None)),
 393: ('000407',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000407-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only nut butters (peanut: no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of nut butters (peanut with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one '
       'small glass jar with the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000407.png',
       (None, None)),
 394: ('000408',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000408-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only seed butters (tahini): no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of seed butters (tahini) with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one '
       'small glass jar with the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000408.png',
       (None, None)),
 395: ('000409',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000409-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only plant-based butter: no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of plant-based butter with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one '
       'small glass jar with the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000409.png',
       (None, None)),
 396: ('000410',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000410-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only herb butter: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of herb butter with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass jar '
       'with the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000410.png',
       (None, None)),
 397: ('000411',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000411-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only canned corn: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of canned corn with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one simple closed '
       'can with a small picture of the food on the label and no words.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000411.png',
       (None, None)),
 398: ('000412',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000412-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only canned peas: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of canned peas with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one simple closed '
       'can with a small picture of the food on the label and no words.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/candidates/canned_peas_1773209422.png',
       (None, None)),
 399: ('000413',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000413-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only canned carrots: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of canned carrots with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one simple closed '
       'can with a small picture of the food on the label and no words.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000413.png',
       (None, None)),
 400: ('000414',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000414-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only canned green beans: no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of canned green beans with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one '
       'simple closed can with a small picture of the food on the label and no words.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000414.png',
       (None, None)),
 401: ('000415',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000415-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only canned tomatoes: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of canned tomatoes with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one simple closed '
       'can with a small picture of the food on the label and no words.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/candidates/canned_tomatoes_1773209426.png',
       (None, None)),
 402: ('000416',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000416-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only canned beets: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of canned beets with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one simple closed '
       'can with a small picture of the food on the label and no words.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/candidates/canned_beets_1773209419.png',
       (None, None)),
 403: ('000417',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000417-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only canned mixed vegetables: no '
       'other foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background '
       '(#FFFFFF), no colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or '
       'numbers. A vector art illustration of canned mixed vegetables with subtle natural surface texture and soft '
       'shading, so the material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered '
       'framing. Show one simple closed can with a small picture of the food on the label and no words.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000417.png',
       (None, None)),
 404: ('000418',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000418-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only canned spinach: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of canned spinach with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one simple closed '
       'can with a small picture of the food on the label and no words.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000418.png',
       (None, None)),
 405: ('000419',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000419-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only canned peaches: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of canned peaches with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one simple closed '
       'can with a small picture of the food on the label and no words.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000419.png',
       (None, None)),
 406: ('000420',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000420-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only canned pears: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of canned pears with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one simple closed '
       'can with a small picture of the food on the label and no words.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000420.png',
       (None, None)),
 407: ('000421',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000421-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only canned pineapple: no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of canned pineapple with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one '
       'simple closed can with a small picture of the food on the label and no words.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000421.png',
       (None, None)),
 408: ('000422',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000422-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only canned fruit cocktail: no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of canned fruit cocktail with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one '
       'simple closed can with a small picture of the food on the label and no words.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000422.png',
       (None, None)),
 409: ('000423',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000423-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only canned cherries: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of canned cherries with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one simple closed '
       'can with a small picture of the food on the label and no words.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000423.png',
       (None, None)),
 410: ('000424',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000424-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only canned oranges: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of canned oranges with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one simple closed '
       'can with a small picture of the food on the label and no words.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000424.png',
       (None, None)),
 411: ('000425',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000425-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only canned applesauce: no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of canned applesauce with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one '
       'simple closed can with a small picture of the food on the label and no words.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000425.png',
       (None, None)),
 412: ('000426',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000426-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only canned chickpeas: no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of canned chickpeas with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one '
       'simple closed can with a small picture of the food on the label and no words.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000426.png',
       (None, None)),
 413: ('000427',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000427-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only canned black beans: no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of canned black beans with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one '
       'simple closed can with a small picture of the food on the label and no words.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000427.png',
       (None, None)),
 414: ('000428',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000428-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only canned kidney beans: no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of canned kidney beans with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one '
       'simple closed can with a small picture of the food on the label and no words.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000428.png',
       (None, None)),
 415: ('000429',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000429-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only canned lentils: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of canned lentils with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one simple closed '
       'can with a small picture of the food on the label and no words.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000429.png',
       (None, None)),
 416: ('000430',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000430-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only canned cannellini beans: no '
       'other foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background '
       '(#FFFFFF), no colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or '
       'numbers. A vector art illustration of canned cannellini beans with subtle natural surface texture and soft '
       'shading, so the material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered '
       'framing. Show one simple closed can with a small picture of the food on the label and no words.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000430.png',
       (None, None)),
 417: ('000431',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000431-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only canned navy beans: no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of canned navy beans with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one '
       'simple closed can with a small picture of the food on the label and no words.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000431.png',
       (None, None)),
 418: ('000432',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000432-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only canned pinto beans: no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of canned pinto beans with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one '
       'simple closed can with a small picture of the food on the label and no words.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000432.png',
       (None, None)),
 419: ('000433',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000433-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only canned tuna in water: no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of canned tuna in water with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000433.png',
       (None, None)),
 420: ('000434',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000434-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only canned tuna in oil: no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of canned tuna in oil with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000434.png',
       (None, None)),
 421: ('000435',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000435-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only canned salmon: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of canned salmon with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000435.png',
       (None, None)),
 422: ('000436',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000436-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only canned sardines: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of canned sardines with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000436.png',
       (None, None)),
 423: ('000437',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000437-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only canned mackerel: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of canned mackerel with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000437.png',
       (None, None)),
 424: ('000438',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000438-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only canned anchovies: no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of canned anchovies with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000438.png',
       (None, None)),
 425: ('000439',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000439-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only canned crab: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of canned crab with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000439.png',
       (None, None)),
 426: ('000440',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000440-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only canned clams: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of canned clams with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000440.png',
       (None, None)),
 427: ('000441',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000441-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only canned chicken: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of canned chicken with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one simple closed '
       'can with a small picture of the food on the label and no words.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000441.png',
       (None, None)),
 428: ('000442',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000442-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only canned beef: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of canned beef with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one simple closed '
       'can with a small picture of the food on the label and no words.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000442.png',
       (None, None)),
 429: ('000443',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000443-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only canned ham: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of canned ham with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one simple closed can with '
       'a small picture of the food on the label and no words.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000443.png',
       (None, None)),
 430: ('000444',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000444-v3.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only corned beef: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of corned beef with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one simple closed '
       'can with a small picture of the food on the label and no words. Show only one closed can with a small picture '
       'of corned beef on the label, with nothing next to it.',
       ('Show only one closed can with a small picture of corned beef on the label, with nothing next to it.', None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000444.png',
       (None, None)),
 431: ('000445',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000445-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only canned spam: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of canned spam with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one simple closed '
       'can with a small picture of the food on the label and no words.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000445.png',
       (None, None)),
 432: ('000446',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000446-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only pickled cucumbers (dill '
       'pickles): no other foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white '
       'background (#FFFFFF), no colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, '
       'letters or numbers. A vector art illustration of pickled cucumbers (dill pickles) with subtle natural surface '
       'texture and soft shading, so the material reads clearly (grain, skin, rind, crumb), while staying clean and '
       'simple. Centered framing. Show one glass jar with the food visible inside.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000446.png',
       (None, None)),
 433: ('000447',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000447-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only bread and butter pickles: no '
       'other foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background '
       '(#FFFFFF), no colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or '
       'numbers. A vector art illustration of bread and butter pickles with subtle natural surface texture and soft '
       'shading, so the material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered '
       'framing. Show one glass jar with the food visible inside.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000447.png',
       (None, None)),
 434: ('000448',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000448-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only pickled beets: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of pickled beets with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one glass jar with '
       'the food visible inside.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000448.png',
       (None, None)),
 435: ('000449',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000449-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only pickled onions: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of pickled onions with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one glass jar with '
       'the food visible inside.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000449.png',
       (None, None)),
 436: ('000450',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000450-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only pickled jalapeños: no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of pickled jalapeños with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one '
       'glass jar with the food visible inside.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000450.png',
       (None, None)),
 437: ('000451',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000451-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only pickled cabbage: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of pickled cabbage with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one glass jar with '
       'the food visible inside.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000451.png',
       (None, None)),
 438: ('000452',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000452-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only canned coconut milk: no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of canned coconut milk with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one '
       'simple closed can with a coconut on the label and no words.',
       (None, 'Show one simple closed can with a coconut on the label and no words.'),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000452.png',
       (None, 'Show one simple closed can with a coconut on the label and no words.')),
 439: ('000453',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000453-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only béchamel: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of béchamel with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass jar with '
       'the sauce visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000453.png',
       (None, None)),
 440: ('000454',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000454-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only velouté: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of velouté with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass jar with '
       'the sauce visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000454.png',
       (None, None)),
 441: ('000455',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000455-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only espagnole: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of espagnole with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass jar with '
       'the sauce visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000455.png',
       (None, None)),
 442: ('000456',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000456-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only hollandaise: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of hollandaise with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass jar '
       'with the sauce visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000456.png',
       (None, None)),
 443: ('000457',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000457-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only tomato (mother sauce): no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of tomato (mother sauce) with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one '
       'small glass jar with the sauce visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000457.png',
       (None, None)),
 444: ('000459',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000459-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only demi-glace: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of demi-glace with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass jar with '
       'the sauce visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000459.png',
       (None, None)),
 445: ('000460',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000460-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only beef gravy: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of beef gravy with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass jar with '
       'the sauce visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000460.png',
       (None, None)),
 446: ('000461',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000461-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only turkey gravy: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of turkey gravy with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass jar '
       'with the sauce visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000461.png',
       (None, None)),
 447: ('000462',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000462-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only sausage gravy: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of sausage gravy with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass jar '
       'with the sauce visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000462.png',
       (None, None)),
 448: ('000463',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000463-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only red wine reduction: no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of red wine reduction with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one '
       'small glass jar with the sauce visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000463.png',
       (None, None)),
 449: ('000464',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000464-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only mushroom gravy: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of mushroom gravy with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass jar '
       'with the sauce visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000464.png',
       (None, None)),
 450: ('000465',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000465-v2.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only peppercorn sauce: no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of peppercorn sauce with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one '
       'small glass jar with the sauce visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000465.png',
       (None, None)),
 451: ('000466',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000466-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only pan jus: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of pan jus with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass jar with '
       'the sauce visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000466.png',
       (None, None)),
 452: ('000467',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000467-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only lemon butter sauce: no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of lemon butter sauce with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one '
       'small glass jar with the sauce visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000467.png',
       (None, None)),
 453: ('000468',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000468-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only marinara: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of marinara with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass jar with '
       'the sauce visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000468.png',
       (None, None)),
 454: ('000469',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000469-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only pomodoro: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of pomodoro with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass jar with '
       'the sauce visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000469.png',
       (None, None)),
 455: ('000470',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000470-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only bolognese: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of bolognese with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass jar with '
       'the sauce visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000470.png',
       (None, None)),
 456: ('000471',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000471-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only arrabbiata: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of arrabbiata with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass jar with '
       'the sauce visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000471.png',
       (None, None)),
 457: ('000472',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000472-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only pizza sauce: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of pizza sauce with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass jar '
       'with the sauce visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000472.png',
       (None, None)),
 458: ('000473',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000473-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only putanesca: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of putanesca with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass jar with '
       'the sauce visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000473.png',
       (None, None)),
 459: ('000474',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000474-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only tomato cream sauce: no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of tomato cream sauce with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one '
       'small glass jar with the sauce visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000474.png',
       (None, None)),
 460: ('000475',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000475-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only alfredo: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of alfredo with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass jar with '
       'the sauce visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000475.png',
       (None, None)),
 461: ('000476',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000476-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only mornay: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of mornay with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass jar with '
       'the sauce visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000476.png',
       (None, None)),
 462: ('000477',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000477-v2.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only carbonara: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of carbonara with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass jar with '
       'the sauce visible. Show only the sauce in the jar, with no pasta, bacon or anything else around it.',
       ('Show only the sauce in the jar, with no pasta, bacon or anything else around it.', None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000477.png',
       (None, None)),
 463: ('000478',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000478-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only four cheese sauce: no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of four cheese sauce with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one '
       'small glass jar with the sauce visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000478.png',
       (None, None)),
 464: ('000479',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000479-v2.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only blue cheese sauce: no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of blue cheese sauce with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one '
       'small glass jar with the sauce visible. Show the sauce in a small glass jar, not on a plate.',
       ('Show the sauce in a small glass jar, not on a plate.', None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000479.png',
       (None, None)),
 465: ('000480',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000480-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only gorgonzola sauce: no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of gorgonzola sauce with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one '
       'small glass jar with the sauce visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000480.png',
       (None, None)),
 466: ('000481',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000481-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only creamy garlic sauce: no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of creamy garlic sauce with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one '
       'small glass jar with the sauce visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000481.png',
       (None, None)),
 467: ('000482',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000482-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only soy sauce: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of soy sauce with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one glass bottle with a '
       'cork stopper and the sauce visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000482.png',
       (None, None)),
 468: ('000483',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000483-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only teriyaki sauce: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of teriyaki sauce with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one glass bottle '
       'with a cork stopper and the sauce visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/candidates/teriyaki_sauce_1773209497.png',
       (None, None)),
 469: ('000484',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000484-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only hoisin sauce: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of hoisin sauce with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one glass bottle '
       'with a cork stopper and the sauce visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000484.png',
       (None, None)),
 470: ('000485',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000485-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only oyster sauce: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of oyster sauce with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one glass bottle '
       'with a cork stopper and the sauce visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000485.png',
       (None, None)),
 471: ('000486',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000486-v2.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only sweet and sour sauce: no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of sweet and sour sauce with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one '
       'glass bottle with a cork stopper and the sauce visible. sweet and sour bottle looks different. Use a tall, '
       'narrow glass bottle with a cork stopper like the other sauces, not a round one.',
       ('Use a tall, narrow glass bottle with a cork stopper like the other sauces, not a round one.', None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000486.png',
       (None, None)),
 472: ('000487',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000487-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only fish sauce: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of fish sauce with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one glass bottle with a '
       'cork stopper and the sauce visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000487.png',
       (None, None)),
 473: ('000488',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000488-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only gochujang: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of gochujang with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one glass bottle with a '
       'cork stopper and the sauce visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000488.png',
       (None, None)),
 474: ('000489',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000489-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only peanut sauce: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of peanut sauce with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one glass bottle '
       'with a cork stopper and the sauce visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000489.png',
       (None, None)),
 475: ('000490',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000490-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only ponzu: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of ponzu with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one glass bottle with a '
       'cork stopper and the sauce visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000490.png',
       (None, None)),
 476: ('000491',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000491-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only tamarind sauce: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of tamarind sauce with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one glass bottle '
       'with a cork stopper and the sauce visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000491.png',
       (None, None)),
 477: ('000492',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000492-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only basil pesto: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of basil pesto with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass jar '
       'with the sauce visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000492.png',
       (None, None)),
 478: ('000493',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000493-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only sun-dried tomato pesto: no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of sun-dried tomato pesto with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one '
       'small glass jar with the sauce visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000493.png',
       (None, None)),
 479: ('000494',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000494-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only cilantro pesto: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of cilantro pesto with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass jar '
       'with the sauce visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000494.png',
       (None, None)),
 480: ('000495',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000495-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only parsley sauce (salsa verde): no '
       'other foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background '
       '(#FFFFFF), no colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or '
       'numbers. A vector art illustration of parsley sauce (salsa verde) with subtle natural surface texture and soft '
       'shading, so the material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered '
       'framing. Show one small glass jar with the sauce visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000495.png',
       (None, None)),
 481: ('000496',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000496-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only chimichurri: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of chimichurri with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass jar '
       'with the sauce visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000496.png',
       (None, None)),
 482: ('000497',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000497-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only gremolata: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of gremolata with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass jar with '
       'the sauce visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000497.png',
       (None, None)),
 483: ('000498',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000498-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only mint sauce: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of mint sauce with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass jar with '
       'the sauce visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000498.png',
       (None, None)),
 484: ('000499',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000499-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only zhoug: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of zhoug with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass jar with '
       'the sauce visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000499.png',
       (None, None)),
 485: ('000500',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000500-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only balsamic vinaigrette: no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of balsamic vinaigrette with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one '
       'glass bottle with a cork stopper and the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000500.png',
       (None, None)),
 486: ('000501',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000501-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only red wine vinaigrette: no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of red wine vinaigrette with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one '
       'glass bottle with a cork stopper and the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000501.png',
       (None, None)),
 487: ('000502',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000502-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only honey mustard dressing: no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of honey mustard dressing with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one '
       'glass bottle with a cork stopper and the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000502.png',
       (None, None)),
 488: ('000503',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000503-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only ranch dressing: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of ranch dressing with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one glass bottle '
       'with a cork stopper and the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000503.png',
       (None, None)),
 489: ('000504',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000504-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only caesar dressing: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of caesar dressing with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one glass bottle '
       'with a cork stopper and the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000504.png',
       (None, None)),
 490: ('000505',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000505-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only italian dressing: no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of italian dressing with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one '
       'glass bottle with a cork stopper and the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000505.png',
       (None, None)),
 491: ('000506',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000506-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only thousand island: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of thousand island with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one glass bottle '
       'with a cork stopper and the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000506.png',
       (None, None)),
 492: ('000507',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000507-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only green goddess dressing: no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of green goddess dressing with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one '
       'glass bottle with a cork stopper and the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000507.png',
       (None, None)),
 493: ('000508',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000508-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only aioli: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of aioli with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass jar with '
       'the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000508.png',
       (None, None)),
 494: ('000509',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000509-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only tzatziki: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of tzatziki with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass jar with '
       'the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000509.png',
       (None, None)),
 495: ('000510',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000510-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only sriracha mayo: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of sriracha mayo with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass jar '
       'with the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000510.png',
       (None, None)),
 496: ('000511',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000511-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only garlic dip: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of garlic dip with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass jar with '
       'the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000511.png',
       (None, None)),
 497: ('000512',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000512-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only hummus: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of hummus with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass jar with '
       'the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000512.png',
       (None, None)),
 498: ('000513',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000513-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only buffalo sauce: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of buffalo sauce with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass jar '
       'with the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000513.png',
       (None, None)),
 499: ('000515',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000515-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only sweet chili sauce: no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of sweet chili sauce with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one '
       'small glass jar with the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000515.png',
       (None, None)),
 500: ('000516',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000516-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only cheese dip: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of cheese dip with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass jar with '
       'the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000516.png',
       (None, None)),
 501: ('000517',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000517-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only queso: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of queso with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass jar with '
       'the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000517.png',
       (None, None)),
 502: ('000518',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000518-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only ketchup: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of ketchup with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass jar with '
       'the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000518.png',
       (None, None)),
 503: ('000519',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000519-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only mustard: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of mustard with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass jar with '
       'the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000519.png',
       (None, None)),
 504: ('000520',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000520-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only mayonnaise: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of mayonnaise with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass jar with '
       'the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000520.png',
       (None, None)),
 505: ('000521',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000521-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only bbq sauce: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of bbq sauce with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass jar with '
       'the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000521.png',
       (None, None)),
 506: ('000522',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000522-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only hot sauce: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of hot sauce with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass jar with '
       'the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000522.png',
       (None, None)),
 507: ('000523',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000523-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only horseradish: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of horseradish with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass jar '
       'with the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000523.png',
       (None, None)),
 508: ('000525',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000525-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only worcestershire sauce: no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of worcestershire sauce with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one '
       'small glass jar with the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000525.png',
       (None, None)),
 509: ('000526',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000526-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only tahini: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of tahini with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass jar with '
       'the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000526.png',
       (None, None)),
 510: ('000527',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000527-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only chili crisp: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of chili crisp with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass jar '
       'with the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000527.png',
       (None, None)),
 511: ('000529',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000529-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only maple syrup: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of maple syrup with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass jar '
       'with the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000529.png',
       (None, None)),
 512: ('000530',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000530-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only fruit jam: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of fruit jam with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass jar with '
       'the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000530.png',
       (None, None)),
 513: ('000531',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000531-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only fruit jelly: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of fruit jelly with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass jar '
       'with the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000531.png',
       (None, None)),
 514: ('000532',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000532-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only apple butter: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of apple butter with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass jar '
       'with the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000532.png',
       (None, None)),
 515: ('000533',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000533-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only nutella: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of nutella with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass jar with '
       'the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000533.png',
       (None, None)),
 516: ('000534',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000534-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only peanut butter: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of peanut butter with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass jar '
       'with the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000534.png',
       (None, None)),
 517: ('000535',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000535-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only almond butter: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of almond butter with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass jar '
       'with the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000535.png',
       (None, None)),
 518: ('000536',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000536-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only dulce de leche: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of dulce de leche with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass jar '
       'with the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000536.png',
       (None, None)),
 519: ('000537',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000537-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only chocolate sauce: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of chocolate sauce with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass jar '
       'with the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000537.png',
       (None, None)),
 520: ('000538',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000538-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only dill pickles: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of dill pickles with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one glass jar with '
       'the food visible inside.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000538.png',
       (None, None)),
 521: ('000540',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000540-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only sweet pickle relish: no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of sweet pickle relish with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one '
       'glass jar with the food visible inside.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000540.png',
       (None, None)),
 522: ('000541',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000541-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only corn relish: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of corn relish with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one glass jar with '
       'the food visible inside.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000541.png',
       (None, None)),
 523: ('000542',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000542-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only chow-chow: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of chow-chow with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one glass jar with the food '
       'visible inside.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000542.png',
       (None, None)),
 524: ('000543',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000543-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only kimchi: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of kimchi with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one glass jar with the food '
       'visible inside.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000543.png',
       (None, None)),
 525: ('000544',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000544-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only sauerkraut: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of sauerkraut with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one glass jar with the food '
       'visible inside.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000544.png',
       (None, None)),
 526: ('000547',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000547-v2.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only harissa: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of harissa with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass jar with '
       'the sauce visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000547.png',
       (None, None)),
 527: ('000548',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000548-v2.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only romesco: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of romesco with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass jar with '
       'the sauce visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000548.png',
       (None, None)),
 528: ('000549',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000549-v2.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only miso glaze: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of miso glaze with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass jar with '
       'the sauce visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000549.png',
       (None, None)),
 529: ('000550',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000550-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only beurre blanc: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of beurre blanc with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass jar '
       'with the sauce visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000550.png',
       (None, None)),
 530: ('000551',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000551-v2.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only curry sauce: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of curry sauce with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass jar '
       'with the sauce visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000551.png',
       (None, None)),
 531: ('000552',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000552-v2.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only tartar sauce: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of tartar sauce with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass jar '
       'with the sauce visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000552.png',
       (None, None)),
 532: ('000553',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000553-v2.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only cranberry sauce: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of cranberry sauce with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass jar '
       'with the sauce visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000553.png',
       (None, None)),
 533: ('000554',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000554-v2.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only raita: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of raita with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass jar with '
       'the sauce visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000554.png',
       (None, None)),
 534: ('000555',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000555-v2.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only cocktail sauce: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of cocktail sauce with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass jar '
       'with the sauce visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000555.png',
       (None, None)),
 535: ('000556',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000556-v2.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only salsa: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of salsa with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass jar with '
       'the sauce visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000556.png',
       (None, None)),
 536: ('000557',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000557-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only pale ale: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of pale ale with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one glass bottle of it.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000557.png',
       (None, None)),
 537: ('000558',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000558-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only lager: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of lager with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one glass bottle of it.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000558.png',
       (None, None)),
 538: ('000559',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000559-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only pilsner: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of pilsner with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one glass bottle of it.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000559.png',
       (None, None)),
 539: ('000560',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000560-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only stout: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of stout with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one glass bottle of it.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/candidates/stout_1773295371.png',
       (None, None)),
 540: ('000561',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000561-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only porter: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of porter with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one glass bottle of it.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000561.png',
       (None, None)),
 541: ('000562',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000562-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only wheat beer: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of wheat beer with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one glass bottle of it.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000562.png',
       (None, None)),
 542: ('000563',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000563-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only india pale ale (ipa): no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of india pale ale (ipa) with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one '
       'glass bottle of it.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000563.png',
       (None, None)),
 543: ('000564',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000564-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only amber ale: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of amber ale with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one glass bottle of it.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/candidates/amber_ale_1773207830.png',
       (None, None)),
 544: ('000565',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000565-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only saison: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of saison with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one glass bottle of it.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000565.png',
       (None, None)),
 545: ('000566',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000566-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only dry cider: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of dry cider with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one glass bottle of it.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/candidates/dry_cider_1773209405.png',
       (None, None)),
 546: ('000567',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000567-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only sweet cider: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of sweet cider with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one glass bottle of '
       'it.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000567.png',
       (None, None)),
 547: ('000568',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000568-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only sparkling cider: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of sparkling cider with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one glass bottle of '
       'it.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000568.png',
       (None, None)),
 548: ('000569',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000569-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only hard apple cider: no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of hard apple cider with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one '
       'glass bottle of it.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000569.png',
       (None, None)),
 549: ('000570',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000570-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only pear cider (perry): no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of pear cider (perry) with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one '
       'glass bottle of it.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000570.png',
       (None, None)),
 550: ('000571',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000571-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only rosé cider: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of rosé cider with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one glass bottle of it.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000571.png',
       (None, None)),
 551: ('000572',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000572-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only red wine: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of red wine with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one glass of it.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000572.png',
       (None, None)),
 552: ('000573',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000573-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only white wine: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of white wine with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one glass of it.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/candidates/white_wine_1773209415.png',
       (None, None)),
 553: ('000574',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000574-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only rosé wine: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of rosé wine with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one glass of it.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000574.png',
       (None, None)),
 554: ('000575',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000575-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only sparkling wine: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of sparkling wine with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one glass of it.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000575.png',
       (None, None)),
 555: ('000576',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000576-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only dessert wine: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of dessert wine with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one glass of it.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000576.png',
       (None, None)),
 556: ('000577',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000577-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only fortified wine: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of fortified wine with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one glass of it.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000577.png',
       (None, None)),
 557: ('000578',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000578-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only vodka: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of vodka with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass bottle with '
       'the drink visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000578.png',
       (None, None)),
 558: ('000579',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000579-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only whiskey: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of whiskey with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass bottle with '
       'the drink visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000579.png',
       (None, None)),
 559: ('000580',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000580-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only rum: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of rum with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass bottle with '
       'the drink visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000580.png',
       (None, None)),
 560: ('000581',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000581-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only gin: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of gin with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass bottle with '
       'the drink visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/candidates/gin_1773209409.png',
       (None, None)),
 561: ('000582',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000582-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only tequila: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of tequila with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass bottle with '
       'the drink visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000582.png',
       (None, None)),
 562: ('000583',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000583-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only brandy: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of brandy with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass bottle with '
       'the drink visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/candidates/brandy_1773295280.png',
       (None, None)),
 563: ('000584',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000584-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only cognac: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of cognac with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass bottle with '
       'the drink visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/candidates/cognac_1773209321.png',
       (None, None)),
 564: ('000585',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000585-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only mezcal: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of mezcal with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass bottle with '
       'the drink visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/candidates/mezcal_1773295311.png',
       (None, None)),
 565: ('000586',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000586-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only baileys irish cream: no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of baileys irish cream with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one '
       'small glass bottle with the drink visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/candidates/baileys_irish_cream_1773295255.png',
       (None, None)),
 566: ('000587',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000587-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only amaretto: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of amaretto with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass bottle with '
       'the drink visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/candidates/amaretto_1773217264.png',
       (None, None)),
 567: ('000588',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000588-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only kahlúa: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of kahlúa with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass bottle with '
       'the drink visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000588.png',
       (None, None)),
 568: ('000589',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000589-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only triple sec: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of triple sec with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass bottle with '
       'the drink visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/candidates/triple_sec_1773295382.png',
       (None, None)),
 569: ('000590',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000590-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only grand marnier: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of grand marnier with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass '
       'bottle with the drink visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000590.png',
       (None, None)),
 570: ('000591',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000591-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only sambuca: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of sambuca with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass bottle with '
       'the drink visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000591.png',
       (None, None)),
 571: ('000592',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000592-v2.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only campari: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of campari with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass bottle with '
       'the drink visible. missing the top of the bottle',
       ('Show the whole bottle, including the cap.', None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/candidates/campari_1773132924.png',
       (None, None)),
 572: ('000593',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000593-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only limoncello: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of limoncello with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass bottle with '
       'the drink visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/candidates/limoncello_1773209412.png',
       (None, None)),
 573: ('000594',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000594-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only creme de menthe: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of creme de menthe with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass '
       'bottle with the drink visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/candidates/creme_de_menthe_1773209325.png',
       (None, None)),
 574: ('000595',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000595-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only sparkling water: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of sparkling water with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one clear glass of '
       'it.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000595.png',
       (None, None)),
 575: ('000596',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000596-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only orange juice: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of orange juice with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one glass bottle of '
       'it.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000596.png',
       (None, None)),
 576: ('000597',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000597-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only apple juice: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of apple juice with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one glass bottle of '
       'it.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000597.png',
       (None, None)),
 577: ('000598',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000598-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only grape juice: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of grape juice with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one glass bottle of '
       'it.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000598.png',
       (None, None)),
 578: ('000599',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000599-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only pineapple juice: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of pineapple juice with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one glass bottle of '
       'it.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000599.png',
       (None, None)),
 579: ('000600',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000600-v2.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only cranberry juice: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of cranberry juice with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one glass bottle of '
       'it.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000600.png',
       (None, None)),
 580: ('000601',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000601-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only tomato juice: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of tomato juice with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one glass bottle of '
       'it.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000601.png',
       (None, None)),
 581: ('000602',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000602-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only carrot juice: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of carrot juice with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one glass bottle of '
       'it.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000602.png',
       (None, None)),
 582: ('000603',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000603-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only beet juice: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of beet juice with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one glass bottle of it.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000603.png',
       (None, None)),
 583: ('000604',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000604-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only cola: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of cola with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one glass bottle of it.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000604.png',
       (None, None)),
 584: ('000605',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000605-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only lemon-lime soda: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of lemon-lime soda with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one glass bottle of '
       'it.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000605.png',
       (None, None)),
 585: ('000606',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000606-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only root beer: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of root beer with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one glass bottle of it.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000606.png',
       (None, None)),
 586: ('000607',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000607-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only ginger ale: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of ginger ale with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one glass bottle of it.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000607.png',
       (None, None)),
 587: ('000608',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000608-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only tonic water: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of tonic water with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one glass bottle of '
       'it.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000608.png',
       (None, None)),
 588: ('000609',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000609-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only club soda: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of club soda with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one glass bottle of it.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000609.png',
       (None, None)),
 589: ('000610',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000610-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only cream soda: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of cream soda with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one glass bottle of it.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000610.png',
       (None, None)),
 590: ('000611',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000611-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only fruit punch: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of fruit punch with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one glass bottle of '
       'it.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000611.png',
       (None, None)),
 591: ('000612',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000612-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only black tea: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of black tea with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small heap of the dry tea '
       'leaves.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000612.png',
       (None, None)),
 592: ('000613',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000613-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only green tea: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of green tea with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small heap of the dry tea '
       'leaves.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000613.png',
       (None, None)),
 593: ('000614',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000614-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only white tea: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of white tea with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small heap of the dry tea '
       'leaves.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000614.png',
       (None, None)),
 594: ('000615',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000615-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only oolong tea: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of oolong tea with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small heap of the dry tea '
       'leaves.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000615.png',
       (None, None)),
 595: ('000616',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000616-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only herbal tea (e.g. chamomile: no '
       'other foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background '
       '(#FFFFFF), no colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or '
       'numbers. A vector art illustration of herbal tea (e.g. chamomile with subtle natural surface texture and soft '
       'shading, so the material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered '
       'framing. Show a small heap of the dry tea leaves.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000616.png',
       (None, None)),
 596: ('000617',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000617-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only chai: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of chai with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small heap of the dry tea '
       'leaves.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000617.png',
       (None, None)),
 597: ('000618',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000618-v2.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only iced tea: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of iced tea with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one glass of iced tea, with '
       'nothing next to it.',
       (None, 'Show one glass of iced tea, with nothing next to it.'),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000618.png',
       (None, None)),
 598: ('000619',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000619-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only matcha: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of matcha with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small heap of the dry tea '
       'leaves.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000619.png',
       (None, None)),
 599: ('000620',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000620-v2.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only brewed coffee: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of brewed coffee with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one cup or glass of '
       'the drink as it is served, with nothing next to it.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000620.png',
       (None, None)),
 600: ('000621',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000621-v2.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only espresso: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of espresso with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one cup or glass of the '
       'drink as it is served, with nothing next to it.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000621.png',
       (None, None)),
 601: ('000622',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000622-v2.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only americano: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of americano with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one cup or glass of the '
       'drink as it is served, with nothing next to it.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000622.png',
       (None, None)),
 602: ('000623',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000623-v2.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only cappuccino: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of cappuccino with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one cup or glass of the '
       'drink as it is served, with nothing next to it.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000623.png',
       (None, None)),
 603: ('000624',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000624-v2.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only latte: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of latte with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one cup or glass of the '
       'drink as it is served, with nothing next to it.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000624.png',
       (None, None)),
 604: ('000625',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000625-v2.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only macchiato: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of macchiato with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one cup or glass of the '
       'drink as it is served, with nothing next to it.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000625.png',
       (None, None)),
 605: ('000626',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000626-v2.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only cold brew: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of cold brew with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one cup or glass of the '
       'drink as it is served, with nothing next to it.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000626.png',
       (None, None)),
 606: ('000627',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000627-v2.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only iced coffee: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of iced coffee with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one cup or glass of '
       'the drink as it is served, with nothing next to it.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000627.png',
       (None, None)),
 607: ('000628',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000628-v2.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only frappuccino: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of frappuccino with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one cup or glass of '
       'the drink as it is served, with nothing next to it.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000628.png',
       (None, None)),
 608: ('000629',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000629-v2.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only mocha: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of mocha with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one cup or glass of the '
       'drink as it is served, with nothing next to it.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/000629.png',
       (None, None)),
 609: ('000630',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000630-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only bacon: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of bacon with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show the raw, uncooked cut with '
       'its natural color.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/candidates/bacon_1773209463.png',
       (None, None)),
 610: ('IMP-b38735',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/IMP-b38735-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only water: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of water with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one clear glass of it.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/candidates/water_1773209486.png',
       (None, None)),
 611: ('000632',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000632-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only burrata: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of burrata with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one wedge or block.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/candidates/burrata_1773209429.png',
       (None, None)),
 612: ('000633',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000633-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only mozzarella cheese: no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of mozzarella cheese with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one '
       'wedge or block.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/candidates/mozzarella_cheese_1773209433.png',
       (None, None)),
 613: ('000634',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000634-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only pre-baked pizza base: no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of pre-baked pizza base with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one '
       'whole flatbread.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/candidates/pizza_base_pre_baked_1773208791.png',
       (None, None)),
 614: ('000635',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000635-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only chicken bouillon cube: no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of chicken bouillon cube with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one '
       'unwrapped stock cube with nothing else, no container.',
       (None, 'Show one unwrapped stock cube with nothing else, no container.'),
       'https://storage.googleapis.com/thelazychef-assets/pantry/candidates/chicken_bouillon_cube_1773209493.png',
       (None, 'Show one unwrapped stock cube with nothing else, no container.')),
 615: ('000636',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000636-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only pomegranate: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of pomegranate with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show it whole and fresh, '
       'as bought.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/candidates/pomegranate_1773209459.png',
       (None, None)),
 616: ('000637',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000637-v2.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only white vinegar: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of white vinegar with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one glass bottle '
       'with a cork stopper and the vinegar visible.',
       (None, 'Show one glass bottle with a cork stopper and the vinegar visible.'),
       'https://storage.googleapis.com/thelazychef-assets/pantry/candidates/white_vinegar_1773209504.png',
       (None, None)),
 617: ('000638',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000638-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only turkey filet: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of turkey filet with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show the raw, uncooked '
       'cut with its natural color.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/candidates/turkey_filet_1773209482.png',
       (None, None)),
 618: ('000639',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000639-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only beef stock cube: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of beef stock cube with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one unwrapped stock '
       'cube with nothing else, no container.',
       (None, 'Show one unwrapped stock cube with nothing else, no container.'),
       'https://storage.googleapis.com/thelazychef-assets/pantry/candidates/beef_stock_cube_1773209490.png',
       (None, 'Show one unwrapped stock cube with nothing else, no container.')),
 619: ('000640',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000640-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only duck liver: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of duck liver with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show the raw, uncooked cut with '
       'its natural color.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/candidates/duck_liver_1773209479.png',
       (None, None)),
 621: ('IMP-0d29f9',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/IMP-0d29f9-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only lemon juice: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of lemon juice with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one glass bottle of '
       'it.',
       (None, None),
       None,
       (None, None)),
 623: ('IMP-4b0561',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/IMP-4b0561-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only jalapeños: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of jalapeños with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show it whole and fresh, as '
       'bought.',
       (None, None),
       None,
       (None, None)),
 626: ('IMP-2d1f5d',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/IMP-2d1f5d-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only lime juice: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of lime juice with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one glass bottle of it.',
       (None, None),
       None,
       (None, None)),
 629: ('IMP-5a0ea6',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/IMP-5a0ea6-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only chipotle peppers in adobo sauce: '
       'no other foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background '
       '(#FFFFFF), no colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or '
       'numbers. A vector art illustration of chipotle peppers in adobo sauce with subtle natural surface texture and '
       'soft shading, so the material reads clearly (grain, skin, rind, crumb), while staying clean and simple. '
       'Centered framing. Show one simple closed can with a small picture of the food on the label and no words.',
       (None, None),
       None,
       (None, None)),
 634: ('000641',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000641-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only protein yoghurt: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of protein yoghurt with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass jar '
       'with the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/candidates/protein_yoghurt_1773209437.png',
       (None, None)),
 647: ('IMP-4d73fb',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/IMP-4d73fb-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only kalamata olives: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of kalamata olives with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one glass jar with '
       'the food visible inside.',
       (None, None),
       None,
       (None, None)),
 650: ('IMP-fa00e5',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/IMP-fa00e5-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only red onion: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of red onion with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show it whole and fresh, as '
       'bought.',
       (None, None),
       None,
       (None, None)),
 653: ('000642',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000642-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only cucumber: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of cucumber with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show it whole and fresh, as '
       'bought.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/candidates/cucumber_1773217993.png',
       (None, None)),
 654: ('000643',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000643-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only garlic powder: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of garlic powder with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass '
       'spice jar with the spice visible. Fine pale beige powder.',
       ('Fine pale beige powder.', None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/candidates/garlic_powder_1773217972.png',
       ('Fine pale beige powder.', None)),
 655: ('000644',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000644-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only onion powder: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of onion powder with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass '
       'spice jar with the spice visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/candidates/ground_onion_1773217982.png',
       (None, None)),
 656: ('000645',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000645-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only salmon fillet: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of salmon fillet with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show it raw, with its '
       'natural color. Bright orange-pink raw salmon fillet with white fat lines.',
       ('Bright orange-pink raw salmon fillet with white fat lines.', None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/candidates/salmon_fillet_1773217586.png',
       ('Bright orange-pink raw salmon fillet with white fat lines.', None)),
 658: ('000647',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000647-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only avocado: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of avocado with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show it whole and fresh, as '
       'bought.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/candidates/avocado_1773209455.png',
       (None, None)),
 659: ('000648',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000648-v2.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only rice vinegar: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of rice vinegar with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one glass bottle '
       'with a cork stopper and the vinegar visible.',
       (None, 'Show one glass bottle with a cork stopper and the vinegar visible.'),
       'https://storage.googleapis.com/thelazychef-assets/pantry/candidates/rice_vinegar_1773208435.png',
       (None, None)),
 660: ('000649',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000649-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only cornstarch: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of cornstarch with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small paper bag, open at '
       'the top, with the contents visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/candidates/cornstarch_1773208235.png',
       (None, None)),
 662: ('000651',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000651-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only couscous: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of couscous with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small handful of the dry '
       'pasta.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/candidates/couscous_1773208292.png',
       (None, None)),
 663: ('000652',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000652-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only cayenne pepper: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of cayenne pepper with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass '
       'spice jar with the spice visible.',
       (None, None),
       None,
       (None, None)),
 664: ('000653',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000653-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only chili powder: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of chili powder with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass '
       'spice jar with the spice visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/candidates/chili_powder_1773209512.png',
       (None, None)),
 665: ('000654',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000654-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only italian seasoning: no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of italian seasoning with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a '
       'small heap of the dried leaves.',
       (None, None),
       None,
       (None, None)),
 666: ('000655',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000655-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only chili flakes: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of chili flakes with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass '
       'spice jar with the spice visible.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/candidates/chili_flakes_1773209508.png',
       (None, None)),
 667: ('pending-afcc0c4d',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/pending-afcc0c4d-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only guanciale: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of guanciale with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show the raw, uncooked cut with '
       'its natural color.',
       (None, None),
       None,
       (None, None)),
 668: ('pending-ea15f600',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/pending-ea15f600-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only pecorino romano: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of pecorino romano with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one wedge or block.',
       (None, None),
       None,
       (None, None)),
 671: ('pending-eceae956',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/pending-eceae956-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only wasabi paste: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of wasabi paste with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass jar '
       'with the contents visible.',
       (None, None),
       None,
       (None, None)),
 672: ('pending-50b60365',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/pending-50b60365-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only saffron threads: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of saffron threads with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a few whole pieces.',
       (None, None),
       None,
       (None, None)),
 673: ('pending-647e83ba',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/pending-647e83ba-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only bean sprouts: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of bean sprouts with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small heap of '
       'them.',
       (None, None),
       None,
       (None, None)),
 674: ('pending-8af531ec',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/pending-8af531ec-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only peanuts: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of peanuts with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small heap of them.',
       (None, None),
       None,
       (None, None)),
 675: ('pending-2ade5b11',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/pending-2ade5b11-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only star anise: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of star anise with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a few whole pieces. Two or '
       'three whole star-shaped pods.',
       ('Two or three whole star-shaped pods.', None),
       None,
       ('Two or three whole star-shaped pods.', None)),
 677: ('000656',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000656-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only cod: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of cod with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show it raw, with its natural '
       'color.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/candidates/cod_1773208338.png',
       (None, None)),
 678: ('pending-aab153fd',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/pending-aab153fd-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only prosciutto: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of prosciutto with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show the raw, uncooked cut with '
       'its natural color.',
       (None, None),
       None,
       (None, None)),
 679: ('pending-28a3a1d9',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/pending-28a3a1d9-v2.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only balsamic vinegar: no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of balsamic vinegar with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one '
       'glass bottle with a cork stopper and the vinegar visible.',
       (None, 'Show one glass bottle with a cork stopper and the vinegar visible.'),
       None,
       (None, None)),
 680: ('pending-c3a67ec6',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/pending-c3a67ec6-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only boiled ham: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of boiled ham with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show the raw, uncooked cut with '
       'its natural color.',
       (None, None),
       None,
       (None, None)),
 682: ('pending-cb0a72d6',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/pending-cb0a72d6-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only chilli paste: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of chilli paste with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass jar '
       'with the contents visible.',
       (None, None),
       None,
       (None, None)),
 683: ('pending-e1018cf8',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/pending-e1018cf8-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only bay leaf: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of bay leaf with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small heap of the dried '
       'leaves.',
       (None, None),
       None,
       (None, None)),
 684: ('pending-a63176a1',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/pending-a63176a1-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only everything bagel: no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of everything bagel with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one '
       'whole loaf.',
       (None, None),
       None,
       (None, None)),
 685: ('000657',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000657-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only sun-dried tomato: no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of sun-dried tomato with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show it '
       'whole and fresh, as bought.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/candidates/sun_dried_tomato_1773209516.png',
       (None, None)),
 694: ('pending-fedbccba',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/pending-fedbccba-v2.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only breadcrumbs: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of breadcrumbs with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small heap of dry '
       'golden breadcrumbs, with nothing else.',
       (None, 'Show a small heap of dry golden breadcrumbs, with nothing else.'),
       None,
       (None, None)),
 695: ('pending-816c1015',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/pending-816c1015-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only pomegranate molasses: no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of pomegranate molasses with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one '
       'small glass jar with the contents visible.',
       (None, None),
       None,
       (None, None)),
 698: ('000658',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/000658-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only frozen mixed berries: no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of frozen mixed berries with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a '
       'small cluster of the fresh berries.',
       (None, None),
       'https://storage.googleapis.com/thelazychef-assets/pantry/candidates/frozen_mixed_berries_1773758101.png',
       (None, None)),
 699: ('pending-b47b3ef9',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261018-1900/pending-b47b3ef9-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only hamburger buns: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of hamburger buns with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one whole loaf.',
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
