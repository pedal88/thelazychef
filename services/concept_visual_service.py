import json
import logging
from pathlib import Path
from database.models import db, ConceptVisual

logger = logging.getLogger(__name__)

def sync_concept_visuals():
    """Reads JSON config files and upserts missing ConceptVisual records."""
    base_dir = Path(__file__).parent.parent / "data"
    
    # 1. Diets
    diets_path = base_dir / "constraints" / "diets.json"
    if diets_path.exists():
        with open(diets_path) as f:
            data = json.load(f)
            _upsert_concepts('diet', data.get('diets', []))

    # 2. Meal Types
    meal_types_path = base_dir / "constraints" / "meal_types.json"
    if meal_types_path.exists():
        with open(meal_types_path) as f:
            data = json.load(f)
            cls = data.get('meal_classification', {})
            types = []
            for group, items in cls.items():
                types.extend(items)
            _upsert_concepts('meal_type', list(set(types)))

    # 3. Main Protein
    protein_path = base_dir / "constraints" / "main_protein.json"
    if protein_path.exists():
        with open(protein_path) as f:
            data = json.load(f)
            # Use categories as the main protein types
            proteins = [p['category'] for p in data.get('protein_types', []) if 'category' in p]
            _upsert_concepts('main_protein', proteins)

    # 4. Cooking Methods
    methods_path = base_dir / "post_processing" / "cooking_methods.json"
    if methods_path.exists():
        with open(methods_path) as f:
            data = json.load(f)
            methods = [m['method'] for m in data.get('cooking_methods', []) if 'method' in m]
            _upsert_concepts('cooking_method', methods)

    # 5. Cuisines
    cuisines_path = base_dir / "post_processing" / "cuisines.json"
    if cuisines_path.exists():
        with open(cuisines_path) as f:
            data = json.load(f)
            _upsert_concepts('cuisine', data.get('cuisines', []))

    # 6. Categories & Subcategories
    categories_path = base_dir / "constraints" / "categories.json"
    if categories_path.exists():
        with open(categories_path) as f:
            categories_map = json.load(f)
            
            # Upsert Main Categories
            _upsert_concepts('ingredient_category', list(categories_map.keys()))
            
            # Upsert Sub Categories
            sub_cats = []
            for subs in categories_map.values():
                sub_cats.extend(subs)
            _upsert_concepts('ingredient_subcategory', list(set(sub_cats)))


def _upsert_concepts(concept_type: str, names: list[str]):
    """Idempotently insert missing concept names for a given type."""
    if not names:
        return
        
    for name in names:
        name_str = str(name).strip()
        if not name_str: 
            continue
        
        # Check if exists
        exists = db.session.execute(
            db.select(ConceptVisual).filter_by(concept_type=concept_type, concept_name=name_str)
        ).scalar()
        
        if not exists:
            new_visual = ConceptVisual(
                concept_type=concept_type,
                concept_name=name_str,
                image_url=None
            )
            db.session.add(new_visual)

    db.session.commit()
    logger.info(f"Sync complete for {concept_type}")

def get_concept_images_dict():
    """
    Returns a nested dict suited for frontend insertion:
    {
      "diet": {"Vegan": "https://...", "Keto": "https://..."},
      "cuisine": {"Italian": "https://...", ...}
    }
    """
    visuals = db.session.execute(
        db.select(ConceptVisual).where(ConceptVisual.image_url.is_not(None))
    ).scalars().all()

    result = {}
    for v in visuals:
        if v.concept_type not in result:
            result[v.concept_type] = {}
        result[v.concept_type][v.concept_name] = v.image_url
        
    return result
