"""
Canonical Unit Normalization utility.
Used to solve the Pluralization/Abbreviation Trap in culinary string matching.
"""

UNIT_ALIASES: dict[str, str] = {
    # Tablespoons
    'tablespoon': 'tbsp',
    'tablespoons': 'tbsp',
    'tbsp.': 'tbsp',
    'tbsps': 'tbsp',
    'tbs': 'tbsp',
    
    # Teaspoons
    'teaspoon': 'tsp',
    'teaspoons': 'tsp',
    'tsp.': 'tsp',
    'tsps': 'tsp',
    
    # Cups
    'cups': 'cup',
    'c': 'cup',
    
    # Cloves
    'cloves': 'clove',
    
    # Pinches
    'pinches': 'pinch',
    
    # Ounces
    'ounces': 'oz',
    'ounce': 'oz',
    'ozs': 'oz',
    'oz.': 'oz',
    
    # Fluid Ounces
    'fluid ounces': 'fl oz',
    'fluid ounce': 'fl oz',
    'fl. oz.': 'fl oz',
    
    # Grams
    'grams': 'g',
    'gram': 'g',
    'g.': 'g',
    
    # Milliliters
    'milliliters': 'ml',
    'milliliter': 'ml',
    'ml.': 'ml',
    'mls': 'ml'
}

def normalize_unit(unit_string: str) -> str:
    """
    Lowercases, strips, and attempts to resolve a unit string to its canonical form.
    Returns the canonical form if found, else the sanitized original string.
    """
    if not unit_string:
        return ""
        
    cleaned = unit_string.lower().strip()
    return UNIT_ALIASES.get(cleaned, cleaned)
