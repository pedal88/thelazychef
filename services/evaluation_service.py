import os
import json
from pathlib import Path
import typing_extensions as typing
from dotenv import load_dotenv

from google import genai
from google.genai import types
from jinja2 import Environment, FileSystemLoader
from PIL import Image
import requests
from io import BytesIO

from database.models import db, Recipe, RecipeEvaluation
from app import app

# Path resolution for Jinja templates
PROMPTS_DIR = Path(__file__).parent.parent / 'data' / 'prompts'
env = Environment(loader=FileSystemLoader(str(PROMPTS_DIR)))

# Initialize genai client (falling back to .env for local vs injected env vars)
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("GOOGLE_API_KEY environment variable is missing.")

client = genai.Client(api_key=api_key)

class RecipeEvaluationSchema(typing.TypedDict):
    """Strict schema for the LLM recipe QA Output enforcing Chain of Thought."""
    reasoning_name: str
    score_name: int
    reasoning_ingredients: str
    score_ingredients: int
    reasoning_components: str
    score_components: int
    reasoning_amounts: str
    score_amounts: int
    reasoning_steps: str
    score_steps: int
    reasoning_image: str
    score_image: int
    total_score: float

def evaluate_recipe(recipe_id: int) -> dict:
    """
    Evaluates a generated recipe using Gemini 1.5 Pro and stores the results in the DB.
    If the recipe's total_score falls below 50, it triggers an active failure state
    by setting recipe.is_flagged_for_review = True.
    
    Args:
        recipe_id: The primary key of the Recipe to evaluate.
        
    Returns:
        dict: A status dictionary containing the resulting total_score and flag status,
              or raises an exception on error.
    """
    # Fetch the target recipe
    recipe = db.session.get(Recipe, recipe_id)
    if not recipe:
        raise ValueError(f"Recipe with ID {recipe_id} not found.")

    # Flatten the recipe into a simple dictionary for the LLM
    # This prevents the LLM from getting bogged down with SQLAlchemy ORM state.
    recipe_dict = {
        "title": recipe.title,
        "cuisine": recipe.cuisine,
        "diet": recipe.diet,
        "difficulty": recipe.difficulty,
        "prep_time_mins": recipe.prep_time_mins,
        "ingredients": [
            {
                "name": i.ingredient.name, 
                "amount": i.amount, 
                "unit": i.unit, 
                "component": i.component
            } for i in recipe.ingredients
        ],
        "instructions": [
            {
                "step": s.step_number, 
                "phase": s.phase, 
                "component": s.component, 
                "text": s.text
            } for s in recipe.instructions
        ]
    }
    
    recipe_json_str = json.dumps(recipe_dict, indent=2)

    # Render template via pathlib
    try:
        template = env.get_template('recipe_qa/recipe_evaluator.jinja2')
        prompt = template.render(recipe_json=recipe_json_str)
    except Exception as e:
        raise ValueError(f"Failed to render Jinja2 evaluation template: {e}")

    # Try to load the image if it exists using PIL per constraints
    image_obj = None
    if getattr(recipe, 'image_filename', None):
        from app import get_recipe_image_url
        img_url = get_recipe_image_url(recipe)
        try:
            if img_url and img_url.startswith('http'):
                image_response = requests.get(img_url, timeout=10)
                image_response.raise_for_status()
                image_obj = Image.open(BytesIO(image_response.content))
            else:
                image_path = Path(app.root_path) / 'static' / 'recipes' / recipe.image_filename
                if image_path.exists():
                    image_obj = Image.open(image_path)
        except Exception as e:
            print(f"Warning: Failed to load image {img_url} for QA: {e}")
            image_obj = None

    if image_obj:
        payload = [prompt, image_obj]
    else:
        # Fallback if text-only
        prompt += "\n[SYSTEM NOTE: NO IMAGE PROVIDED. Output 'No image provided' for reasoning_image and 0 for score_image.]"
        payload = [prompt]

    # Call Gemini (using default gemini-flash-latest which matches active SDK tier)
    try:
        response = client.models.generate_content(
            model='gemini-flash-latest',
            contents=payload,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=RecipeEvaluationSchema,
                temperature=0.2 # Lower temperature for analytical evaluation
            )
        )
    except Exception as e:
        raise ValueError(f"Gemini API request failed during QA evaluation: {e}")

    # Parse JSON strict output
    try:
        # Pydantic typing parses to a dict dynamically via genai.types
        eval_data = response.parsed if response.parsed else json.loads(response.text)
        if hasattr(eval_data, "__dict__"):
             eval_data = vars(eval_data) # Convert Model object to dict if TypedDict resolves
        elif type(eval_data) is not dict:
             eval_data = dict(eval_data)
    except Exception as e:
        raise ValueError(f"Invalid JSON returned from LLM evaluator: {e}")

    # Cleanup any old evaluation
    if recipe.evaluation:
        db.session.delete(recipe.evaluation)
        db.session.commit()

    # Create new evaluation record
    evaluation = RecipeEvaluation(
        recipe_id=recipe.id,
        score_name=eval_data.get('score_name', 0),
        score_ingredients=eval_data.get('score_ingredients', 0),
        score_components=eval_data.get('score_components', 0),
        score_amounts=eval_data.get('score_amounts', 0),
        score_steps=eval_data.get('score_steps', 0),
        score_image=eval_data.get('score_image', 0),
        total_score=eval_data.get('total_score', 0.0),
        evaluation_details={
            'reasoning_name': eval_data.get('reasoning_name', ''),
            'reasoning_ingredients': eval_data.get('reasoning_ingredients', ''),
            'reasoning_components': eval_data.get('reasoning_components', ''),
            'reasoning_amounts': eval_data.get('reasoning_amounts', ''),
            'reasoning_steps': eval_data.get('reasoning_steps', ''),
            'reasoning_image': eval_data.get('reasoning_image', '')
        }
    )
    
    db.session.add(evaluation)
    
    # Active Failure / Flagging State
    is_flagged = False
    if evaluation.total_score < 50:
        recipe.is_flagged_for_review = True
        is_flagged = True
        print(f"⚠️ QA Alert: Recipe {recipe_id} flagged for review (Score: {evaluation.total_score})")
    else:
        recipe.is_flagged_for_review = False
        
    db.session.commit()
    
    return {
        "status": "success", 
        "total_score": evaluation.total_score,
        "is_flagged": is_flagged
    }
