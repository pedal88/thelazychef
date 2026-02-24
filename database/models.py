from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, Boolean, Text, Float, ForeignKey, DateTime, JSON, Index, UniqueConstraint
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
from typing import Any

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Association table for linking resources to each other
resource_relations = db.Table('resource_relations',
    db.Column('source_id', db.Integer, db.ForeignKey('resource.id'), primary_key=True),
    db.Column('related_id', db.Integer, db.ForeignKey('resource.id'), primary_key=True)
)

# Association table for User Favorites - DEPRECATED (Replaced by UserRecipeInteraction)
# user_favorite_recipes = db.Table('user_favorite_recipes',
#     db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
#     db.Column('recipe_id', db.Integer, db.ForeignKey('recipe.id'), primary_key=True),
#     db.Column('saved_at', db.DateTime, default=datetime.datetime.utcnow)
# )

class UserRecipeInteraction(db.Model):
    __tablename__ = 'user_recipe_interaction'
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), primary_key=True)
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipe.id"), primary_key=True)
    status: Mapped[str] = mapped_column(String, nullable=False) # "pass", "favorite"
    is_super_like: Mapped[bool] = mapped_column(Boolean, default=False)
    timestamp: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="interactions")
    recipe: Mapped["Recipe"] = relationship(back_populates="interactions")

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
    aliases: Mapped[str] = mapped_column(Text, default='[]') # JSON list of synonyms
    is_staple: Mapped[bool] = mapped_column(Boolean, default=False) # User preference: Staple ingredient?
    created_at: Mapped[str] = mapped_column(String, nullable=True) # ISO format date string
    # Lifecycle: 'active' | 'inactive' | 'pending'
    # 'inactive' is a soft-delete — ingredient stays in DB to protect recipe FK relationships.
    # 'pending' = newly imported, awaiting review.
    status: Mapped[str] = mapped_column(String(20), default='active', index=True, nullable=False, server_default='active')

    # Payload (Flattened)
    image_url: Mapped[str] = mapped_column(String, nullable=True)
    image_prompt: Mapped[str] = mapped_column(Text, nullable=True)

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

    recipe_ingredients: Mapped[list["RecipeIngredient"]] = relationship(back_populates="ingredient")
    evaluation: Mapped["IngredientEvaluation"] = relationship(back_populates="ingredient", uselist=False, cascade="all, delete-orphan")


class IngredientEvaluation(db.Model):
    """LLM-as-a-Judge QA result for a single Ingredient (One-to-One)."""
    __tablename__ = 'ingredient_evaluation'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ingredient_id: Mapped[int] = mapped_column(ForeignKey("ingredient.id"), unique=True, nullable=False)

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
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipe.id"), primary_key=True)
    meal_type: Mapped[str] = mapped_column(String, primary_key=True)


class RecipeDiet(db.Model):
    """Many-to-many link between Recipe and diet labels.

    Mirrors RecipeMealType: a recipe can satisfy multiple diets
    (e.g. both 'vegan' and 'gluten-free').
    """
    __tablename__ = 'recipe_diet'
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipe.id"), primary_key=True)
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

    # New Metadata
    chef_id: Mapped[str] = mapped_column(ForeignKey("chef.id"), nullable=True)
    is_flagged_for_review: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    # Publishing State Machine: 'draft' | 'approved' | 'rejected'
    # Every AI-generated recipe starts as 'draft' — invisible to public routes.
    status: Mapped[str] = mapped_column(String(20), default='draft', index=True, nullable=False, server_default='draft')
    taste_level: Mapped[int] = mapped_column(Integer, nullable=True) # 1-5
    prep_time_mins: Mapped[int] = mapped_column(Integer, nullable=True) # snapped to time.json
    cleanup_factor: Mapped[int] = mapped_column(Integer, nullable=True)

    # Nutrition Totals (Calculated)
    total_calories: Mapped[float] = mapped_column(Float, nullable=True)
    total_protein: Mapped[float] = mapped_column(Float, nullable=True)
    total_carbs: Mapped[float] = mapped_column(Float, nullable=True)
    total_fat: Mapped[float] = mapped_column(Float, nullable=True)
    total_fiber: Mapped[float] = mapped_column(Float, nullable=True)
    total_sugar: Mapped[float] = mapped_column(Float, nullable=True)

    instructions: Mapped[list["Instruction"]] = relationship(back_populates="recipe", cascade="all, delete-orphan")
    ingredients: Mapped[list["RecipeIngredient"]] = relationship(back_populates="recipe", cascade="all, delete-orphan")
    chef: Mapped["Chef"] = relationship(back_populates="recipes")
    meal_types: Mapped[list["RecipeMealType"]] = relationship(cascade="all, delete-orphan")
    diets: Mapped[list["RecipeDiet"]] = relationship(cascade="all, delete-orphan")
    evaluation: Mapped["RecipeEvaluation"] = relationship(back_populates="recipe", uselist=False, cascade="all, delete-orphan")

    @property
    def meal_types_list(self) -> list[str]:
        return [fmt.meal_type for fmt in self.meal_types]

    @property
    def diets_list(self) -> list[str]:
        return [rd.diet for rd in self.diets]

    interactions: Mapped[list["UserRecipeInteraction"]] = relationship(back_populates="recipe", cascade="all, delete-orphan")
    collections: Mapped[list["CollectionItem"]] = relationship(back_populates="recipe", cascade="all, delete-orphan")
    queue_items: Mapped[list["UserQueue"]] = relationship(back_populates="recipe", cascade="all, delete-orphan")

class Instruction(db.Model):
    __tablename__ = 'instruction'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipe.id"), nullable=False)
    phase: Mapped[str] = mapped_column(String, nullable=False) # "Prep", "Cook", "Serve"
    component: Mapped[str] = mapped_column(String(100), nullable=False, default="Main Dish") # NEW: e.g., "The Steak", "The Sauce"
    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)

    recipe: Mapped["Recipe"] = relationship(back_populates="instructions")

class RecipeEvaluation(db.Model):
    __tablename__ = 'recipe_evaluation'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipe.id"), unique=True, nullable=False)
    
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
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipe.id"), nullable=False)
    ingredient_id: Mapped[int] = mapped_column(ForeignKey("ingredient.id"), nullable=False)
    amount: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String)
    component: Mapped[str] = mapped_column(String, default="Main", nullable=False)

    recipe: Mapped["Recipe"] = relationship(back_populates="ingredients")
    ingredient: Mapped["Ingredient"] = relationship(back_populates="recipe_ingredients")

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
        ForeignKey('recipe_collection.id'), primary_key=True
    )
    recipe_id: Mapped[int] = mapped_column(
        ForeignKey('recipe.id'), primary_key=True
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
    user_id: Mapped[int] = mapped_column(ForeignKey('user.id'), nullable=False, index=True)
    recipe_id: Mapped[int] = mapped_column(ForeignKey('recipe.id'), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    added_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow, nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="queue_items")
    recipe: Mapped["Recipe"] = relationship(back_populates="queue_items")
