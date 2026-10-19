"""ingredient symbols symbols-20261019-1411

New ingredient symbols from run symbols-20261019-1411, approved in review: 41
ingredients get the new image_url and image_prompt, and image_notes and
image_form with any changes from review. 0 rejected ones keep
their image and get their review changes. The images are in
gs://thelazychef-assets/pantry/symbols/symbols-20261019-1411/.

Downgrade restores the old image_url, image_notes and image_form. The old
image_prompt is not kept: it belonged to the retired image pipeline.

Made by scripts/ingredient_symbols.py promote.

Revision ID: edb2c0f81d8a
Revises: 9482c2b9d672
Create Date: 2026-10-19

"""
from alembic import op
import sqlalchemy as sa


revision = 'edb2c0f81d8a'
down_revision = '9482c2b9d672'
branch_labels = None
depends_on = None

# id: (food_id, new_url, new_prompt, (new_notes, new_form), old_url, (old_notes, old_form))
APPROVED = {700: ('000659',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261019-1411/000659-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only fresh ginger: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of fresh ginger with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show it whole and fresh, '
       'as bought.',
       (None, None),
       None,
       (None, None)),
 701: ('000660',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261019-1411/000660-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only chicken stock: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of chicken stock with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass jar '
       'with the sauce visible.',
       (None, None),
       None,
       (None, None)),
 702: ('000661',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261019-1411/000661-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only vegetable stock: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of vegetable stock with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass jar '
       'with the sauce visible.',
       (None, None),
       None,
       (None, None)),
 703: ('000662',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261019-1411/000662-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only beef stock: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of beef stock with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass jar with '
       'the sauce visible.',
       (None, None),
       None,
       (None, None)),
 704: ('000663',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261019-1411/000663-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only tomato paste: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of tomato paste with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one simple closed '
       'can with a small picture of the food on the label and no words.',
       (None, None),
       None,
       (None, None)),
 705: ('000664',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261019-1411/000664-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only passata: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of passata with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one simple closed can with '
       'a small picture of the food on the label and no words.',
       (None, None),
       None,
       (None, None)),
 706: ('000665',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261019-1411/000665-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only thai red curry paste: no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of thai red curry paste with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one '
       'glass bottle with a cork stopper and the sauce visible.',
       (None, None),
       None,
       (None, None)),
 707: ('000666',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261019-1411/000666-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only thai green curry paste: no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of thai green curry paste with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one '
       'glass bottle with a cork stopper and the sauce visible.',
       (None, None),
       None,
       (None, None)),
 708: ('000667',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261019-1411/000667-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only kaffir lime leaves: no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of kaffir lime leaves with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a '
       'small bunch.',
       (None, None),
       None,
       (None, None)),
 709: ('000668',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261019-1411/000668-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only thai basil: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of thai basil with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small bunch.',
       (None, None),
       None,
       (None, None)),
 710: ('000669',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261019-1411/000669-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only galangal: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of galangal with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show it whole and fresh, as '
       'bought.',
       (None, None),
       None,
       (None, None)),
 711: ('000670',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261019-1411/000670-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only jasmine rice: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of jasmine rice with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small paper bag, '
       'open at the top, with the contents visible.',
       (None, None),
       None,
       (None, None)),
 712: ('000671',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261019-1411/000671-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only basmati rice: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of basmati rice with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small paper bag, '
       'open at the top, with the contents visible.',
       (None, None),
       None,
       (None, None)),
 713: ('000672',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261019-1411/000672-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only arborio rice: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of arborio rice with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small paper bag, '
       'open at the top, with the contents visible.',
       (None, None),
       None,
       (None, None)),
 714: ('000673',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261019-1411/000673-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only sushi rice: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of sushi rice with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small paper bag, open at '
       'the top, with the contents visible.',
       (None, None),
       None,
       (None, None)),
 715: ('000674',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261019-1411/000674-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only garam masala: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of garam masala with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass '
       'spice jar with the spice visible.',
       (None, None),
       None,
       (None, None)),
 716: ('000675',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261019-1411/000675-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only curry powder: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of curry powder with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass '
       'spice jar with the spice visible.',
       (None, None),
       None,
       (None, None)),
 717: ('000676',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261019-1411/000676-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only red lentils: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of red lentils with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small heap of '
       'them.',
       (None, None),
       None,
       (None, None)),
 718: ('000677',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261019-1411/000677-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only paneer: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of paneer with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one wedge or block.',
       (None, None),
       None,
       (None, None)),
 719: ('000678',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261019-1411/000678-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only fenugreek: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of fenugreek with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small heap of the dried '
       'leaves.',
       (None, None),
       None,
       (None, None)),
 720: ('000679',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261019-1411/000679-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only curry leaves: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of curry leaves with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small bunch.',
       (None, None),
       None,
       (None, None)),
 721: ('000680',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261019-1411/000680-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only asafoetida: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of asafoetida with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass spice jar '
       'with the spice visible.',
       (None, None),
       None,
       (None, None)),
 722: ('000681',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261019-1411/000681-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only mirin: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of mirin with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one glass bottle with a '
       'cork stopper and the sauce visible.',
       (None, None),
       None,
       (None, None)),
 723: ('000682',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261019-1411/000682-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only sake: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of sake with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one glass of it.',
       (None, None),
       None,
       (None, None)),
 724: ('000683',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261019-1411/000683-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only miso paste: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of miso paste with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one glass bottle with a '
       'cork stopper and the sauce visible.',
       (None, None),
       None,
       (None, None)),
 725: ('000684',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261019-1411/000684-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only nori: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of nori with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing.',
       (None, None),
       None,
       (None, None)),
 726: ('000685',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261019-1411/000685-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only dashi: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of dashi with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one glass bottle with a '
       'cork stopper and the sauce visible.',
       (None, None),
       None,
       (None, None)),
 727: ('000686',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261019-1411/000686-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only panko: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of panko with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one whole loaf.',
       (None, None),
       None,
       (None, None)),
 728: ('000687',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261019-1411/000687-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only udon noodles: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of udon noodles with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small bundle of '
       'the dry noodles.',
       (None, None),
       None,
       (None, None)),
 729: ('000688',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261019-1411/000688-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only soba noodles: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of soba noodles with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small bundle of '
       'the dry noodles.',
       (None, None),
       None,
       (None, None)),
 730: ('000689',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261019-1411/000689-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only tofu: no other foods, props, '
       'garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of tofu with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small heap of them.',
       (None, None),
       None,
       (None, None)),
 731: ('000690',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261019-1411/000690-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only shaoxing wine: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of shaoxing wine with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one glass of it.',
       (None, None),
       None,
       (None, None)),
 732: ('000691',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261019-1411/000691-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only dark soy sauce: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of dark soy sauce with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one glass bottle '
       'with a cork stopper and the sauce visible.',
       (None, None),
       None,
       (None, None)),
 733: ('000692',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261019-1411/000692-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only chinese five spice: no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of chinese five spice with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one '
       'small glass spice jar with the spice visible.',
       (None, None),
       None,
       (None, None)),
 734: ('000693',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261019-1411/000693-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only sichuan peppercorns: no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of sichuan peppercorns with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a '
       'few whole pieces.',
       (None, None),
       None,
       (None, None)),
 735: ('000694',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261019-1411/000694-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only black bean sauce: no other '
       'foods, props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no '
       'colored backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A '
       'vector art illustration of black bean sauce with subtle natural surface texture and soft shading, so the '
       'material reads clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one '
       'glass bottle with a cork stopper and the sauce visible.',
       (None, None),
       None,
       (None, None)),
 736: ('000695',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261019-1411/000695-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only water chestnuts: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of water chestnuts with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one simple closed '
       'can with a small picture of the food on the label and no words.',
       (None, None),
       None,
       (None, None)),
 737: ('000696',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261019-1411/000696-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only wonton wrappers: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of wonton wrappers with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one whole '
       'flatbread.',
       (None, None),
       None,
       (None, None)),
 738: ('000697',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261019-1411/000697-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only coconut cream: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of coconut cream with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one simple glass '
       'bottle of it.',
       (None, None),
       None,
       (None, None)),
 739: ('000698',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261019-1411/000698-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only palm sugar: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of palm sugar with subtle natural surface texture and soft shading, so the material reads clearly '
       '(grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show a small paper bag, open at '
       'the top, with the contents visible.',
       (None, None),
       None,
       (None, None)),
 740: ('000699',
       'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-20261019-1411/000699-v1.webp',
       'An ingredient symbol for a recipe app, recognizable at small sizes. Show only tamarind paste: no other foods, '
       'props, garnish, utensils, hands, pouring, splashes or scene. Plain pure white background (#FFFFFF), no colored '
       'backdrop, no shadow box. Centered, filling about 80% of the frame. No text, letters or numbers. A vector art '
       'illustration of tamarind paste with subtle natural surface texture and soft shading, so the material reads '
       'clearly (grain, skin, rind, crumb), while staying clean and simple. Centered framing. Show one small glass jar '
       'with the contents visible.',
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
