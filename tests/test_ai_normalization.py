
import unittest
from unittest.mock import MagicMock, patch
import json
import sys
import os

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import ai_engine
from ai_engine import generate_recipe_ai
from ai_engine import generate_recipe_ai

class TestComponentNormalization(unittest.TestCase):
    @patch('ai_engine.client.models.generate_content')
    def test_single_component_normalization(self, mock_generate):
        # Setup Mock Response
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "title": "Test Recipe",
            "cuisine": "Italian",
            "diet": "Non-Vegetarian",
            "difficulty": "Medium",
            "protein_type": "Pork",
            "meal_types": ["Dinner"],
            "chef_id": "gourmet",
            "cleanup_factor": 3,
            "taste_level": 5,
            "prep_time_mins": 30,
            "chef_note": "Enjoy!",
            "components": [
                {
                    "name": "Carbonara Sauce", 
                    "steps": [{"step_number": 1, "phase": "Cook", "text": "Mix eggs and cheese."}]
                }
            ],
            "ingredient_groups": [
                {
                    # MISMATCH HERE: "Main Dish" vs "Carbonara Sauce"
                    "component": "Main Dish", 
                    "ingredients": [{"name": "Eggs", "amount": 2, "unit": "large"}]
                }
            ]
        })
        mock_response.parsed = None # Simulate fallback to JSON parsing or just use text
        mock_generate.return_value = mock_response

        # Run
        recipe = generate_recipe_ai("make carbonara")

        # Assert
        self.assertEqual(len(recipe.components), 1)
        self.assertEqual(len(recipe.ingredient_groups), 1)
        
        # KEY ASSERTION: The ingredient group component should be updated to match the component name
        self.assertEqual(recipe.ingredient_groups[0].component, "Carbonara Sauce")
        print("✅ Normalization Successful: 'Main Dish' -> 'Carbonara Sauce'")

if __name__ == '__main__':
    unittest.main()
