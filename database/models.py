from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, validates
from sqlalchemy import String, Integer, Boolean, Text, Float, ForeignKey, DateTime, JSON, UniqueConstraint
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
from typing import Any, Optional
from pgvector.sqlalchemy import Vector

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Association table for linking resources to each other
resource_relations = db.Table('resource_relations',
    db.Column('source_id', db.Integer, db.ForeignKey('resource.id', ondelete='CASCADE'), primary_key=True),
    db.Column('related_id', db.Integer, db.ForeignKey('resource.id', ondelete='CASCADE'), primary_key=True)
)

# Association table for User Favorites - DEPRECATED (Replaced by UserRecipeInteraction)
# user_favorite_recipes = db.Table('user_favorite_recipes',
#     db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
#     db.Column('recipe_id', db.Integer, db.ForeignKey('recipe.id'), primary_key=True),
#     db.Column('saved_at', db.DateTime, default=datetime.datetime.utcnow)
# )

class UserRecipeInteraction(db.Model):
    __tablename__ = 'user_recipe_interaction'
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete='CASCADE'), primary_key=True)
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipe.id", ondelete='CASCADE'), primary_key=True)
    status: Mapped[str] = mapped_column(String, nullable=False) # "pass", "favorite"
    is_super_like: Mapped[bool] = mapped_column(Boolean, default=False)
    timestamp: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    
    # New Unified Recipe Library Fields
    is_made: Mapped[bool] = mapped_column(Boolean, default=False, server_default='0')
    rating: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    user_photos: Mapped[list] = mapped_column(JSON, default=list, server_default='[]')

    user: Mapped["User"] = relationship(back_populates="interactions")
    recipe: Mapped["Recipe"] = relationship(back_populates="interactions")

class ConceptVisual(db.Model):
    """Stores generated images/icons for abstract culinary metadata like 'diet', 'cuisine', etc."""
    __tablename__ = 'concept_visual'
    __table_args__ = (
        UniqueConstraint('concept_type', 'concept_name', name='uq_concept_visual_type_name'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    concept_type: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    concept_name: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

class VisualStyleGuide(db.Model):
    __tablename__ = 'visual_style_guide'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scope: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    base_wrapper: Mapped[str] = mapped_column(Text, nullable=False)
    negative_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    remove_background: Mapped[bool] = mapped_column(Boolean, default=False, server_default='0')


class Resource(db.Model):
    __tablename__ = 'resource'
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(100), unique=True, nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    summary = db.Column(db.String(500))
    content_markdown = db.Column(db.Text)  # Stores the raw markdown
    image_filename = db.Column(db.String(255))
    
    # 1. Tag Column (User Choice: 1)
    tags = db.Column(db.String(255))
    
    # Status (Draft vs Published)
    status = db.Column(db.String(20), default='draft', index=True)
    
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # 2. Smart Linking (User Choice: 2B)
    related_resources = db.relationship(
        'Resource',
        secondary=resource_relations,
        primaryjoin=(resource_relations.c.source_id == id),
        secondaryjoin=(resource_relations.c.related_id == id),
        backref=db.backref('related_to', lazy='dynamic'),
        lazy='dynamic'
    )

    def get_tag_list(self):
        """Helper to split tags string into a list"""
        if self.tags:
            return [t.strip() for t in self.tags.split(',') if t.strip()]
        return []

    @property
    def meta(self):
        return {'read_time': self.calculate_read_time()}

    def calculate_read_time(self):
        if not self.content_markdown:
             return 1
        word_count = len(self.content_markdown.split())
        return max(1, round(word_count / 200))


class Ingredient(db.Model):
    __tablename__ = 'ingredient'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    food_id: Mapped[str] = mapped_column(String, unique=True, index=True) # Must preserve leading zeros (e.g., "000322")
    name: Mapped[str] = mapped_column(String, index=True) # Display name (e.g., "Avocado")

    # Classification
    main_category: Mapped[str] = mapped_column(String, nullable=True)
    sub_category: Mapped[str] = mapped_column(String, nullable=True)
    tags: Mapped[str] = mapped_column(String, nullable=True) # A comma-separated string for attributes like "keto,vegan,perishable"

    # Physics (Smart Units)
    default_unit: Mapped[str] = mapped_column(String, default='g')
    average_g_per_unit: Mapped[float] = mapped_column(Float, nullable=True) # The weight of 1 unit in grams.

    # Intelligence
    is_staple: Mapped[bool] = mapped_column(Boolean, default=False) # User preference: Staple ingredient?
    created_at: Mapped[str] = mapped_column(String, nullable=True) # ISO format date string
    # Lifecycle: 'active' | 'inactive' | 'pending'
    # 'inactive' is a soft-delete — ingredient stays in DB to protect recipe FK relationships.
    # 'pending' = newly imported, awaiting review.
    status: Mapped[str] = mapped_column(String(20), default='active', index=True, nullable=False, server_default='active')
    # Pantry tier (RECIPE_MODEL_V2.md, "Kjerne og lang hale"): 'core' is what most dishes need and is
    # curated in full; 'long_tail' is kept because a recipe needs it. Null = not reviewed yet.
    tier: Mapped[Optional[str]] = mapped_column(String(12), nullable=True, index=True)
    # The base ingredient a variant belongs to ("thai basil" -> "basil"): substitutions and grouping later.
    base_ingredient_id: Mapped[Optional[int]] = mapped_column(ForeignKey("ingredient.id", ondelete='SET NULL'), nullable=True)

    # Payload (Flattened)
    image_url: Mapped[str] = mapped_column(String, nullable=True)
    has_transparent_image: Mapped[bool] = mapped_column(Boolean, default=False, server_default='0')
    image_prompt: Mapped[str] = mapped_column(Text, nullable=True)
    # Ingredient symbol inputs (services/ingredient_symbols.py). image_form
    # replaces the sub-category rule for ingredients that do not fit it
    # ("one unwrapped stock cube, no container"); image_notes adds details
    # ("pale pink, clearly poultry, not salmon"). image_prompt keeps the
    # prompt the current image was made with.
    image_form: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    image_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    data_source: Mapped[str] = mapped_column(String(50), nullable=False, default='placeholder', server_default='placeholder')

    # AI Embedding (768 dimensions for Google models)
    embedding: Mapped[Optional[Any]] = mapped_column(Vector(768), nullable=True)

    # Nutrition Columns
    calories_per_100g: Mapped[float] = mapped_column(Float, nullable=True)
    kj_per_100g: Mapped[float] = mapped_column(Float, nullable=True)
    protein_per_100g: Mapped[float] = mapped_column(Float, nullable=True)
    carbs_per_100g: Mapped[float] = mapped_column(Float, nullable=True)
    fat_per_100g: Mapped[float] = mapped_column(Float, nullable=True)
    fat_saturated_per_100g: Mapped[float] = mapped_column(Float, nullable=True)
    sugar_per_100g: Mapped[float] = mapped_column(Float, nullable=True)
    fiber_per_100g: Mapped[float] = mapped_column(Float, nullable=True)
    sodium_mg_per_100g: Mapped[float] = mapped_column(Float, nullable=True)
    cholesterol_mg_per_100g: Mapped[float] = mapped_column(Float, nullable=True)
    calcium_mg_per_100g: Mapped[float] = mapped_column(Float, nullable=True)
    potassium_mg_per_100g: Mapped[float] = mapped_column(Float, nullable=True)

    recipe_ingredients: Mapped[list["RecipeIngredient"]] = relationship(back_populates="ingredient")
    # passive_deletes='all': the ORM must not unlink v2 lines when an ingredient is deleted.
    # The foreign key blocks the delete instead, as for recipe_ingredient. Merge first.
    recipe_lines: Mapped[list["RecipeLine"]] = relationship(back_populates="ingredient", passive_deletes='all')
    base_ingredient: Mapped[Optional["Ingredient"]] = relationship(remote_side="Ingredient.id")
    evaluation: Mapped["IngredientEvaluation"] = relationship(back_populates="ingredient", uselist=False, cascade="all, delete-orphan")
    alias_entries: Mapped[list["IngredientAlias"]] = relationship(back_populates="ingredient", cascade="all, delete-orphan", order_by="IngredientAlias.id")

    # Sub-recipe link: if set, this ingredient IS a recipe (e.g. "Chilli Mayo")
    sub_recipe_id: Mapped[Optional[int]] = mapped_column(ForeignKey("recipe.id", ondelete='SET NULL'), nullable=True)
    sub_recipe: Mapped[Optional["Recipe"]] = relationship(
        "Recipe",
        foreign_keys=[sub_recipe_id],
        primaryjoin="Ingredient.sub_recipe_id == Recipe.id",
    )

    # Knowledge Factory: link to the auto-generated "Official Deep Dive" article
    primary_resource_id: Mapped[Optional[int]] = mapped_column(ForeignKey("resource.id", ondelete='SET NULL'), nullable=True)
    primary_resource: Mapped[Optional["Resource"]] = relationship(
        "Resource",
        foreign_keys=[primary_resource_id],
    )

    @validates('name')
    def _normalize_name(self, key, value):
        """Names are stored in lower case with single spaces; views decide the casing."""
        return " ".join(value.split()).lower() if value else value

    @property
    def aliases(self) -> list[str]:
        """Other names that resolve to this ingredient."""
        return [a.name for a in self.alias_entries]


class IngredientAlias(db.Model):
    """Another name for an ingredient ("scallion" for "spring onion").

    The matcher checks aliases after exact names and before fuzzy matching.
    Merging two ingredients moves the loser's aliases to the winner and adds
    the loser's name. Names are stored lower case and unique, so one alias
    always points at one ingredient.
    """
    __tablename__ = 'ingredient_alias'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ingredient_id: Mapped[int] = mapped_column(ForeignKey("ingredient.id", ondelete='CASCADE'), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)

    ingredient: Mapped["Ingredient"] = relationship(back_populates="alias_entries")


class IngredientEvaluation(db.Model):
    """LLM-as-a-Judge QA result for a single Ingredient (One-to-One)."""
    __tablename__ = 'ingredient_evaluation'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ingredient_id: Mapped[int] = mapped_column(ForeignKey("ingredient.id", ondelete='CASCADE'), unique=True, nullable=False)

    # Individual criterion scores (1-100)
    score_image:      Mapped[int] = mapped_column(Integer, nullable=True)
    score_nutrition:  Mapped[int] = mapped_column(Integer, nullable=True)
    score_taxonomy:   Mapped[int] = mapped_column(Integer, nullable=True)
    score_utility:    Mapped[int] = mapped_column(Integer, nullable=True)
    # score_commonness is informational only — excluded from total_score average
    score_commonness: Mapped[int] = mapped_column(Integer, nullable=True)

    # Weighted average of (image, nutrition, taxonomy, utility) only
    total_score: Mapped[float] = mapped_column(Float, nullable=True)

    # Full Chain-of-Thought JSON blob
    evaluation_details: Mapped[dict] = mapped_column(JSON, default=dict)

    ingredient: Mapped["Ingredient"] = relationship(back_populates="evaluation")


class Chef(db.Model):
    __tablename__ = 'chef'
    id: Mapped[str] = mapped_column(String, primary_key=True) # e.g. "french_classic"
    name: Mapped[str] = mapped_column(String, nullable=False)
    archetype: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(Text)
    image_filename: Mapped[str] = mapped_column(String)
    
    # Store complex JSON constraints as strings for now
    constraints: Mapped[str] = mapped_column(Text, default='{}') 
    diet_preferences: Mapped[str] = mapped_column(Text, default='[]')
    cooking_style: Mapped[str] = mapped_column(Text, default='{}')
    ingredient_logic: Mapped[str] = mapped_column(Text, default='{}')
    instruction_style: Mapped[str] = mapped_column(Text, default='{}')

    recipes: Mapped[list["Recipe"]] = relationship(back_populates="chef")

class RecipeMealType(db.Model):
    __tablename__ = 'recipe_meal_type'
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipe.id", ondelete='CASCADE'), primary_key=True)
    meal_type: Mapped[str] = mapped_column(String, primary_key=True)


class RecipeDiet(db.Model):
    """Many-to-many link between Recipe and diet labels.

    Mirrors RecipeMealType: a recipe can satisfy multiple diets
    (e.g. both 'vegan' and 'gluten-free').
    """
    __tablename__ = 'recipe_diet'
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipe.id", ondelete='CASCADE'), primary_key=True)
    diet: Mapped[str] = mapped_column(String, primary_key=True)

class Recipe(db.Model):
    __tablename__ = 'recipe'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    cuisine: Mapped[str] = mapped_column(String)
    # diet column removed — replaced by RecipeDiet join table
    difficulty: Mapped[str] = mapped_column(String)
    protein_type: Mapped[str] = mapped_column(String, nullable=True)
    image_filename: Mapped[str] = mapped_column(String, nullable=True)
    source_image_filename: Mapped[str] = mapped_column(String, nullable=True)

    # New Metadata
    base_servings: Mapped[int] = mapped_column(Integer, default=4, server_default='4')
    chef_id: Mapped[str] = mapped_column(ForeignKey("chef.id"), nullable=True)
    # A version of another recipe made by a chef persona points at the base dish (always the root, never a version)
    base_recipe_id: Mapped[Optional[int]] = mapped_column(ForeignKey("recipe.id", ondelete='SET NULL'), nullable=True, index=True)
    # The language the recipe's text is written in, ISO 639-1 ('en', 'nb'); None when not known (services/recipe_v2/language.py)
    language: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    # The dish image (image_filename): how one serving is presented, the prompt it was made from and the style
    # (services/recipe_v2/images.py, RECIPE_VISUALIZATIONS.md 9.7)
    plating: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    hero_image_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    image_style: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    # Image trial (temporary): images in other styles, made on request and shown only to admins who switch to
    # them: {style: {"dish": filename, "parts": {component local_id: filename}, "notes": [...]}}
    image_variants: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    is_flagged_for_review: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    # Publishing State Machine: 'draft' | 'approved' | 'rejected'
    # Every AI-generated recipe starts as 'draft' — invisible to public routes.
    status: Mapped[str] = mapped_column(String(20), default='draft', index=True, nullable=False, server_default='draft')
    taste_level: Mapped[int] = mapped_column(Integer, nullable=True) # 1-5
    prep_time_mins: Mapped[int] = mapped_column(Integer, nullable=True) # snapped to time.json
    cleanup_factor: Mapped[int] = mapped_column(Integer, nullable=True)

    # Source Tracking (Manual vs AI URL vs AI Prompt)
    source_input: Mapped[str] = mapped_column(String(500), nullable=True)
    source_type: Mapped[str] = mapped_column(String(50), default='manual', server_default='manual')

    # Recipe model v2 (docs/RECIPE_MODEL_V2.md). schema_version 1 = the old lists
    # (ingredients, instructions), 2 = the graph (components, lines, steps).
    schema_version: Mapped[int] = mapped_column(Integer, default=1, server_default='1', nullable=False)
    # Goes up when the content changes (lines, steps, amounts, text), not for status or images.
    revision: Mapped[int] = mapped_column(Integer, default=1, server_default='1', nullable=False)
    revised_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, nullable=True)
    source_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # round 1 text, for restructuring later
    validation_errors: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)  # empty or null when valid
    chef_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    yield_text: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)  # "én form på 24 cm", for recipes not scaled per serving
    # v2 metadata. heat_source is derived from the steps (services/recipe_v2/derive.py); the rest comes from the model.
    heat_source: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # id in derive.HEAT_SOURCES
    spice_level: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 0 mild .. 3 very hot
    keeps_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # leftovers in the fridge; 0 = eat at once
    freezes: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    # Nutrition Totals (Calculated)
    total_calories: Mapped[float] = mapped_column(Float, nullable=True)
    total_protein: Mapped[float] = mapped_column(Float, nullable=True)
    total_carbs: Mapped[float] = mapped_column(Float, nullable=True)
    total_fat: Mapped[float] = mapped_column(Float, nullable=True)
    total_saturated_fat: Mapped[float] = mapped_column(Float, nullable=True)
    total_fiber: Mapped[float] = mapped_column(Float, nullable=True)
    total_sugar: Mapped[float] = mapped_column(Float, nullable=True)
    total_cholesterol_mg: Mapped[float] = mapped_column(Float, nullable=True)
    total_sodium_mg: Mapped[float] = mapped_column(Float, nullable=True)
    total_calcium_mg: Mapped[float] = mapped_column(Float, nullable=True)
    total_potassium_mg: Mapped[float] = mapped_column(Float, nullable=True)
    
    # Nested mapping of component names to image URLs/filenames
    component_images: Mapped[dict] = mapped_column(JSON, default=dict, server_default='{}')

    # AI-generated hook texts (e.g. native_social, cinematic_result)
    social_hooks: Mapped[dict] = mapped_column(JSON, default=dict, server_default='{}')

    # Knowledge Factory: link to the auto-generated "Official Deep Dive" article
    primary_resource_id: Mapped[Optional[int]] = mapped_column(ForeignKey("resource.id", ondelete='SET NULL'), nullable=True)
    primary_resource: Mapped[Optional["Resource"]] = relationship(
        "Resource",
        foreign_keys=[primary_resource_id],
    )

    instructions: Mapped[list["Instruction"]] = relationship(back_populates="recipe", cascade="all, delete-orphan")
    ingredients: Mapped[list["RecipeIngredient"]] = relationship(back_populates="recipe", cascade="all, delete-orphan")
    components: Mapped[list["RecipeComponent"]] = relationship(back_populates="recipe", cascade="all, delete-orphan", order_by="RecipeComponent.sort_order")
    steps: Mapped[list["RecipeStep"]] = relationship(back_populates="recipe", cascade="all, delete-orphan", order_by="RecipeStep.sort_order")
    lines: Mapped[list["RecipeLine"]] = relationship(back_populates="recipe", cascade="all, delete-orphan", order_by="RecipeLine.sort_order")
    chef: Mapped["Chef"] = relationship(back_populates="recipes")
    base_recipe: Mapped[Optional["Recipe"]] = relationship(remote_side="Recipe.id", backref="versions")
    meal_types: Mapped[list["RecipeMealType"]] = relationship(cascade="all, delete-orphan")
    diets: Mapped[list["RecipeDiet"]] = relationship(cascade="all, delete-orphan")
    evaluation: Mapped["RecipeEvaluation"] = relationship(back_populates="recipe", uselist=False, cascade="all, delete-orphan")

    @property
    def meal_types_list(self) -> list[str]:
        return [fmt.meal_type for fmt in self.meal_types]

    @property
    def diets_list(self) -> list[str]:
        return [rd.diet for rd in self.diets]

    @property
    def total_weight_g(self) -> float:
        """Sums up the physical gram weight of all ingredients for 'per 100g' nutrition calculations."""
        return sum([float(i.gram_weight) for i in self.ingredients if i.gram_weight]) or 0.0

    interactions: Mapped[list["UserRecipeInteraction"]] = relationship(back_populates="recipe", cascade="all, delete-orphan")
    collections: Mapped[list["CollectionItem"]] = relationship(back_populates="recipe", cascade="all, delete-orphan")
    queue_items: Mapped[list["UserQueue"]] = relationship(back_populates="recipe", cascade="all, delete-orphan")

class Instruction(db.Model):
    __tablename__ = 'instruction'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipe.id", ondelete='CASCADE'), nullable=False)
    phase: Mapped[str] = mapped_column(String, nullable=False) # "Prep", "Cook", "Serve"
    component: Mapped[str] = mapped_column(String(100), nullable=False, default="Main Dish") # NEW: e.g., "The Steak", "The Sauce"
    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    estimated_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    global_order_index: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    recipe: Mapped["Recipe"] = relationship(back_populates="instructions")

class RecipeEvaluation(db.Model):
    __tablename__ = 'recipe_evaluation'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipe.id", ondelete='CASCADE'), unique=True, nullable=False)
    
    score_name: Mapped[int] = mapped_column(Integer) # 1-100 scale
    score_ingredients: Mapped[int] = mapped_column(Integer) # 1-100 scale
    score_components: Mapped[int] = mapped_column(Integer) # 1-100 scale
    score_amounts: Mapped[int] = mapped_column(Integer) # 1-100 scale
    score_steps: Mapped[int] = mapped_column(Integer) # 1-100 scale
    score_image: Mapped[int] = mapped_column(Integer, nullable=True) # 1-100 scale, nullable for text-only recipes
    
    total_score: Mapped[float] = mapped_column(Float)
    
    evaluation_details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    
    recipe: Mapped["Recipe"] = relationship(back_populates="evaluation")

class RecipeIngredient(db.Model):
    __tablename__ = 'recipe_ingredient'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipe.id", ondelete='CASCADE'), nullable=False)
    ingredient_id: Mapped[int] = mapped_column(ForeignKey("ingredient.id"), nullable=False)
    amount: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String)
    prep_style: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    gram_weight: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    component: Mapped[str] = mapped_column(String, default="Main", nullable=False)

    recipe: Mapped["Recipe"] = relationship(back_populates="ingredients")
    ingredient: Mapped["Ingredient"] = relationship(back_populates="recipe_ingredients")

# ---------------------------------------------------------------------------
# Recipe model v2: the recipe as a graph (docs/RECIPE_MODEL_V2.md, section 5).
# local_id ("c1", "i3", "s2") is the id inside the recipe, used in step text
# ({i3}) and by the AI. Rows hang off the recipe and go with it on delete.
# ---------------------------------------------------------------------------

# after: the steps whose food goes into this step.
recipe_step_after = db.Table('recipe_step_after',
    db.Column('step_id', db.Integer, db.ForeignKey('recipe_step.id', ondelete='CASCADE'), primary_key=True),
    db.Column('after_step_id', db.Integer, db.ForeignKey('recipe_step.id', ondelete='CASCADE'), primary_key=True),
)


class RecipeComponent(db.Model):
    """A part of the dish you can point at, or a sauce made on its own: "Kjøttsaus", "Ris"."""
    __tablename__ = 'recipe_component'
    __table_args__ = (UniqueConstraint('recipe_id', 'local_id', name='uq_recipe_component_local_id'),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipe.id", ondelete='CASCADE'), nullable=False, index=True)
    local_id: Mapped[str] = mapped_column(String(16), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    image_filename: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    # How this part looks in the served dish (services/recipe_v2/appearance.py): '' when it is not seen on its own,
    # None until it has been described
    appearance: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # The dish image this part's image was made from; a new dish image makes it out of date
    image_from: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    recipe: Mapped["Recipe"] = relationship(back_populates="components")


class RecipeStep(db.Model):
    """One action in one place with one "done when". Order is not stored: the planner derives it."""
    __tablename__ = 'recipe_step'
    __table_args__ = (UniqueConstraint('recipe_id', 'local_id', name='uq_recipe_step_local_id'),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipe.id", ondelete='CASCADE'), nullable=False, index=True)
    component_id: Mapped[int] = mapped_column(ForeignKey("recipe_component.id", ondelete='CASCADE'), nullable=False, index=True)
    local_id: Mapped[str] = mapped_column(String(16), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # order in the source, not the plan
    phase: Mapped[str] = mapped_column(String(10), nullable=False)  # prep | cook | serve
    short: Mapped[str] = mapped_column(String(120), nullable=False)
    verb: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)  # the action in short: "kok opp", "stir in"
    text: Mapped[str] = mapped_column(Text, nullable=False)  # template with {iN}
    active_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    passive_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    holds_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # null = no limit
    method: Mapped[str] = mapped_column(String(40), nullable=False)  # id in data/constraints/methods.json
    equipment: Mapped[list] = mapped_column(JSON, nullable=False, default=list)  # ids in equipment.json, first is the cookware
    temp_c: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    mode: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    setup: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    done_when: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    recipe: Mapped["Recipe"] = relationship(back_populates="steps")
    component: Mapped["RecipeComponent"] = relationship()
    lines: Mapped[list["RecipeLine"]] = relationship(back_populates="step", order_by="RecipeLine.sort_order")
    after: Mapped[list["RecipeStep"]] = relationship(
        secondary=recipe_step_after,
        primaryjoin=lambda: RecipeStep.id == recipe_step_after.c.step_id,
        secondaryjoin=lambda: RecipeStep.id == recipe_step_after.c.after_step_id,
        backref="before",
    )


class RecipeLine(db.Model):
    """An ingredient at one moment in the recipe. The same ingredient used twice is two lines.

    step_id is the step that uses the line ("uses" in the model). Every line is used by exactly
    one step, so it is a column here rather than a link table.
    """
    __tablename__ = 'recipe_line'
    __table_args__ = (UniqueConstraint('recipe_id', 'local_id', name='uq_recipe_line_local_id'),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipe.id", ondelete='CASCADE'), nullable=False, index=True)
    component_id: Mapped[int] = mapped_column(ForeignKey("recipe_component.id", ondelete='CASCADE'), nullable=False, index=True)
    step_id: Mapped[int] = mapped_column(ForeignKey("recipe_step.id", ondelete='CASCADE'), nullable=False, index=True)
    # No ondelete: like recipe_ingredient, a used ingredient cannot be deleted, only merged.
    # Null while the ingredient is missing from the pantry; the recipe is then flagged.
    ingredient_id: Mapped[Optional[int]] = mapped_column(ForeignKey("ingredient.id"), nullable=True, index=True)
    local_id: Mapped[str] = mapped_column(String(16), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    name: Mapped[str] = mapped_column(String(200), nullable=False)  # as written in the recipe
    amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # null only for "to taste"
    unit: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # id in data/constraints/units.json
    prep_style: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    cut: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # id in data/constraints/cuts.json
    gram_weight: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    recipe: Mapped["Recipe"] = relationship(back_populates="lines")
    component: Mapped["RecipeComponent"] = relationship()
    step: Mapped["RecipeStep"] = relationship(back_populates="lines")
    ingredient: Mapped[Optional["Ingredient"]] = relationship(back_populates="recipe_lines")


class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationship to interactions
    interactions: Mapped[list["UserRecipeInteraction"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    queue_items: Mapped[list["UserQueue"]] = relationship(back_populates="user", cascade="all, delete-orphan", order_by="UserQueue.position")

    @property
    def favorite_recipes(self):
        """Backward compatibility: returns list of Recipe objects where status is 'favorite'"""
        return [i.recipe for i in self.interactions if i.status == 'favorite']

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


# ---------------------------------------------------------------------------
# Curated Collections
# ---------------------------------------------------------------------------

class RecipeCollection(db.Model):
    """An editorial grouping of recipes (e.g. 'Summer BBQ Favourites')."""
    __tablename__ = 'recipe_collection'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    slug: Mapped[str] = mapped_column(String(150), unique=True, index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    image_filename: Mapped[str] = mapped_column(String(255), nullable=True)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)

    items: Mapped[list["CollectionItem"]] = relationship(
        back_populates="collection",
        cascade="all, delete-orphan",
    )

    @property
    def approved_recipes(self) -> list["Recipe"]:
        """Convenience accessor: only recipes with status='approved'."""
        return [item.recipe for item in self.items if item.recipe.status == 'approved']


class CollectionItem(db.Model):
    """Association object linking a Recipe to a RecipeCollection."""
    __tablename__ = 'collection_item'

    collection_id: Mapped[int] = mapped_column(
        ForeignKey('recipe_collection.id', ondelete='CASCADE'), primary_key=True
    )
    recipe_id: Mapped[int] = mapped_column(
        ForeignKey('recipe.id', ondelete='CASCADE'), primary_key=True
    )
    added_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow, nullable=False
    )

    collection: Mapped["RecipeCollection"] = relationship(back_populates="items")
    recipe: Mapped["Recipe"] = relationship(back_populates="collections")


# ---------------------------------------------------------------------------
# User Cook-Next Queue
# ---------------------------------------------------------------------------

class UserQueue(db.Model):
    """A prioritized 'Cook Next' queue for a logged-in user."""
    __tablename__ = 'user_queue'
    __table_args__ = (
        UniqueConstraint('user_id', 'recipe_id', name='uq_user_queue_recipe'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('user.id', ondelete='CASCADE'), nullable=False, index=True)
    recipe_id: Mapped[int] = mapped_column(ForeignKey('recipe.id', ondelete='CASCADE'), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    added_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow, nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="queue_items")
    recipe: Mapped["Recipe"] = relationship(back_populates="queue_items")


# ---------------------------------------------------------------------------
# Recipe Mirror — Mutual Pairing Links
# ---------------------------------------------------------------------------

class UserLink(db.Model):
    """Tracks a mutual 'Recipe Mirror' connection between two users."""
    __tablename__ = 'user_link'
    __table_args__ = (
        UniqueConstraint('user_id_1', 'user_id_2', name='uq_user_link_pair'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id_1: Mapped[int] = mapped_column(ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    user_id_2: Mapped[Optional[int]] = mapped_column(ForeignKey('user.id', ondelete='CASCADE'), nullable=True)
    pairing_code: Mapped[str] = mapped_column(String(10), unique=True, index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default='PENDING', nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, server_default='0', nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)

    user_1: Mapped["User"] = relationship(foreign_keys=[user_id_1])
    user_2: Mapped[Optional["User"]] = relationship(foreign_keys=[user_id_2])


# ---------------------------------------------------------------------------
# Social Media Content Generation (Media Hub)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Sequence Templates (Media Hub)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# TikTok Source Sidecar
# ---------------------------------------------------------------------------

