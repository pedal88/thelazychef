# Nutritional Engine Overhaul: Architectural Refactoring

## 📊 1. Product & Strategy Overview (For Product Managers)

We have successfully rebuilt the core engine evaluating the health and scientific data of all recipes inside the Lazy Chef ecosystem! 
Historically, the application lacked a deterministic way of accurately mapping precise calories, proteins, and micronutrients. 

**What We Built:**
- **Scientific API Integration:** We abandoned legacy proxy tools and directly authenticated our backend with the professional-grade **Edamam Nutrition Enterprise API**. This means we now extract FDA-level nutritional breakdowns (calories, protein, fiber, calcium, cholesterol, sodium, etc.) natively into our system.
- **The LLM "Fallback" Safety Net:** One major flaw of classical food APIs is dealing with regional or hyper-specific foods (e.g. Scampi, Reindeer Meat, specific French sauces). Instead of displaying blank data and crashing the math, we engineered a custom AI integration. If the Edamam scientific database returns 0 results, the system securely passes the item directly to *Google's Gemini AI* which generates a highly-accurate mathematical estimate, perfectly solving edge cases autonomously!
- **Data Lineage Trust (UI Enhancements):** Transparency is key. Inside our Admin platform, we added beautiful badges that tell you exactly *where* the math came from. You can instantly distinguish between an organically scraped Enterprise API item and an AI-Generated estimate just by clicking on it.
- **Backwards Compatibility:** We implemented a bulk recalculation system. This script dynamically looped through hundreds of existing user recipes in our infrastructure, extracted their ingredients, matched them with the new scientific data, ran the portion multiplication logic, and retroactively updated every recipe ever created in the system with full Nutrition Facts.

---

## 💻 2. Technical Implementation Details (For Developers)

The refactoring introduced several low-level infrastructural shifts to how ingredients, macros, and API network boundaries interact.

### 2.1 Schema Upgrades
The `database/models.py` schema for `Ingredient` was expanded. We injected 11 new Float properties (e.g., `protein_per_100g`, `fat_saturated_per_100g`) and heavily utilized a new String column: `data_source = mapped_column(String(50), default='placeholder')`.
- `data_source` acts as a crucial lineage tag. Its value dictates the integrity and trace logic in the GUI (`edamam_enterprise` or `ai_fallback`). 

### 2.2 The Hybrid Hydration Script Structure
The heavy lifting lives strictly isolated inside `scripts/backfill_nutrition_full.py`. 
- **100g Recalibration Math**: The `fetch_edamam_data()` function overrides and normalizes standard requests. If a database item's `default_unit` is measured in `ml` or `g`, the request aggressively forces the string query into `100 grams [name]` or `100 ml [name]`. This provides exact scientific baselines (dividing the payload total properties relative to the query properties) to get precise scaling logic for recipes.
- **Network Rate-Limiter Throttling**: The Edamam Basic Enterprise pipeline strictly limits developers to 50 Queries Per Minute. The script is protected by an aggressive, non-blocking `time.sleep(1.5)` loop on success paths, heavily prioritizing safety over network speed.
- **Self-Healing Loop**: If a `429 Too Many Requests` status breaks through, the script no longer crashes via `sys.exit(1)`. Instead, a continuous `while < 3 retries` wrapper kicks in, forcefully sleeping the process for an exact 60-second delay window to legally flush the server-side cooldown cap.
- **Gemini Fallback Mechanism (`ai_fallback`)**: If the API returns valid HTTP-200 JSON but `totalWeight` is 0, execution branches logic to `generate_nutrition_estimate(name)`. This method invokes Google GenAI dynamically (`gemini-2.5-flash` with Temp=0), querying strictly for an 11-key JSON mapping. It casts numeric responses locally into kwargs.
- **Audit Logging**: Any unmapped object salvaged by Gemini strictly logs into `logs/unmapped_ingredients.log`.

### 2.3 The Inspector GUI Logic
The Admin UI in `templates/admin/ingredients_management.html` received direct conditional DOM injections. Depending strictly on the SQL `data_source` property queried against `/api/<id>/inspect`, the JavaScript maps HTML `innerHTML` to strict color-coded Tailwind blocks (Purple for Enterprise, Emerald for `ai_generated` / `ai_fallback`). Legacy `edamam_rapidapi` handling logic was safely aggressively removed from the UI.

### 2.4 Mass Recalculator Implementation
Finally, `scripts/recalculate_all_recipes.py` leverages the modular separation established in `services/recipe_service.py` to target historical data hydration.
- It bypasses `generate_recipe` and explicitly executes `recalculate_recipe_nutrition(recipe_id: int, db_session)`.
- The engine iteratively plows through the active SQL cursor pool (`db.session.query(Recipe).all()`), iterating through deeply nested `r_ing in recipe.ingredients`. 
- Commit blocks are throttled locally (`count_updated % 50 == 0`) isolating memory pools from transaction bloat locking out cloud clusters.
