# Prompt Engineering Guide: The Lego Block System

## Overview
The AI prompt logic has been refactored into a **Component-Based (Lego)** architecture using Jinja2 templates. Instead of hardcoding prompts in Python strings, we now use modular templates located in `data/prompts/`.

This system allows you to update "Global Rules" once and have them instantly apply to all generation methods (Text, Web, Video).

## Directory Structure
```
data/prompts/
├── partials/                 # SHARED Lego Blocks
│   ├── global_rules.jinja2   # Rules that apply to EVERYTHING (e.g. Metric, Safety, English)
│   └── json_output.jinja2    # The shared JSON schema definition
│
└── recipe_text/              # TASK-SPECIFIC Templates
    ├── recipe_generation.jinja2  # For "Idea" generation ("Make me a pasta")
    ├── web_extraction.jinja2     # For URL scraping
    └── video_extraction.jinja2   # For Video analysis
```

## How to Make Updates (Best Practices)

### Scenario 1: "I want to add a new safety rule for ALL AI agents."
**Action**: Edit `data/prompts/partials/global_rules.jinja2`.
**Example**: Adding "Always warn about allergens."
**Effect**: This rule will immediately be injected into:
*   Recipe Generation (Idea)
*   Web Extraction
*   Video Extraction

### Scenario 2: "I want to change the JSON output structure."
**Action**: Edit `data/prompts/partials/json_output.jinja2`.
**Example**: Adding a new field like `"total_cost_estimate": float`.
**Effect**: All agents will now be instructed to output this new field.
**Note**: You must also update the Pydantic models in `ai_engine.py` to handle the new field if you want to parse it in Python.

### Scenario 3: "I want to improve how the AI handles Video Captions."
**Action**: Edit `data/prompts/recipe_text/video_extraction.jinja2`.
**Effect**: This only changes the Video workflow. The Web and Idea workflows remain untouched.

### Scenario 4: "I want to change the 'Chef Personality'."
**Action**:
*   For **Idea Generation**: Edit `data/prompts/recipe_text/recipe_generation.jinja2`. This template specifically accepts a `{{ chef_context }}` variable.
*   For **Extraction (Web/Video)**: These are currently "Data Engineer" roles (neutral). You can modify their specific templates to adopt a persona if desired.

## Testing Your Changes
Since rules are shared, a breakage in `json_output.jinja2` breaks EVERYTHING.
**Rule of Thumb**: always test the **"Idea Generation"** route first (`/new-recipe` -> submit query) after changing a partial. It is the fastest way to validate the structure.

## Git Workflow
When tuning prompts:
1.  Create a branch: `git checkout -b tune-prompts-v1`
2.  Make changes to the `.jinja2` files.
3.  Test locally.
4.  Commit: `git commit -m "Prompt: Enforce strict metric units in global_rules"`
5.  Merge.
