import logging
from database.models import db, VisualStyleGuide

logger = logging.getLogger(__name__)

import os
import json

TAXONOMY_CONTEXTS_FILE = os.path.join(os.getcwd(), 'data', 'constraints', 'taxonomy_contexts.json')

def get_taxonomy_contexts() -> dict:
    if not os.path.exists(TAXONOMY_CONTEXTS_FILE):
        return {
            'cooking method': 'Used as an action-oriented icon in the food app to show how a dish is prepared.',
            'cuisine': 'Used as a cultural symbol in the food app to represent the geographic origin of the recipe.',
            'diet': 'Used as a badge in the food app to indicate nutritional or dietary compliance (e.g. vegan, keto).',
            'main protein': 'Used in the food app to highlight the primary main ingredient of the meal.',
            'meal type': 'Used in the food app to categorize what time of day or format the meal is.',
            'dish type': 'Used in the food app to visually categorize the specific type of dish (e.g. salad, soup).'
        }
    with open(TAXONOMY_CONTEXTS_FILE, 'r') as f:
        return json.load(f)

def set_taxonomy_context(new_category: str, text: str, old_category: str = None):
    contexts = get_taxonomy_contexts()
    if old_category and old_category != new_category and old_category in contexts:
        del contexts[old_category]
    contexts[new_category] = text
    os.makedirs(os.path.dirname(TAXONOMY_CONTEXTS_FILE), exist_ok=True)
    with open(TAXONOMY_CONTEXTS_FILE, 'w') as f:
        json.dump(contexts, f, indent=4)

class VisualOrchestrator:
    @classmethod
    def _get_guide(cls, scope: str) -> VisualStyleGuide | None:
        """Fetch guide from DB."""
        try:
            guide = db.session.execute(
                db.select(VisualStyleGuide).filter_by(scope=scope)
            ).scalar()
            return guide
        except Exception as e:
            logger.error(f"Error fetching VisualStyleGuide for scope {scope}: {e}")
            return None

    @classmethod
    def get_styled_prompt(cls, concept_name: str, scope: str) -> str:
        """
        Fetches the wrapper for the scope and replaces '{name}' with the actual concept.
        Returns the original concept_name if no scope is found.
        """
        guide = cls._get_guide(scope)
        if guide and guide.base_wrapper:
            try:
                clean_name = concept_name
                prompt = guide.base_wrapper
                
                if scope == 'taxonomy':
                    category = None
                    val = None
                    
                    if '::' in clean_name:
                        parts = clean_name.split('::', 1)
                        category = parts[0].strip().lower().replace('_', ' ')
                        val = parts[-1].strip()
                    elif ':' in clean_name:
                        parts = clean_name.split(':', 1)
                        category = parts[0].strip().lower().replace('_', ' ')
                        val = parts[-1].strip()
                        
                    if category and val:
                        context = get_taxonomy_contexts().get(category, f"Used as a categorical icon in a food app to represent the {category} category.")
                        
                        if '{taxonomy_group}' in prompt or '{context}' in prompt:
                            prompt = prompt.replace('{taxonomy_group}', category.title())
                            prompt = prompt.replace('{context}', context)
                            clean_name = val # Just inject the raw name for {name}
                        else:
                            clean_name = f"{val} (Taxonomy Group: {category.title()}. App Context: {context})"
                        
                elif '::' in clean_name:
                    clean_name = clean_name.split('::')[-1].strip()
                elif ':' in clean_name:
                    clean_name = clean_name.split(':')[-1].strip()
                    
                if '{name}' in prompt:
                    return prompt.replace('{name}', clean_name)
                else:
                    return f"{prompt} {clean_name}"
            except Exception as e:
                logger.error(f"Error formatting prompt for {scope}: {e}")
        return concept_name

    @classmethod
    def get_negative_prompt(cls, scope: str) -> str | None:
        """Fetches the negative prompt from the orchestrator scope."""
        guide = cls._get_guide(scope)
        if guide:
            return guide.negative_prompt
        return None

    @classmethod
    def get_processing_rules(cls, scope: str) -> dict:
        """
        Returns whether background removal is required.
        """
        guide = cls._get_guide(scope)
        return {
            "remove_background": guide.remove_background if guide else False
        }
