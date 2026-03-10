import os
import re

routes_file = "routes/media_hub_routes.py"
with open(routes_file, "r") as f:
    content = f.read()

# Replace imports
content = content.replace("from media_hub.snapshotter import build_sandbox_context, VALID_FRAGMENTS", 
                          "from media_hub.snapshotter import build_sandbox_context, VALID_FRAGMENTS, is_valid_fragment")
content = content.replace("from media_hub.snapshotter import VALID_FRAGMENTS", 
                          "from media_hub.snapshotter import VALID_FRAGMENTS, is_valid_fragment")

# Replace validation
content = content.replace("if fragment_name not in VALID_FRAGMENTS:", 
                          "if not is_valid_fragment(fragment_name):")

# Add the new recipe-meta endpoint before the sandbox route
new_route = """
@media_hub_bp.route("/sandbox/api/recipe-meta", methods=["GET"])
@login_required
@admin_required
def get_recipe_meta():
    from database.models import Recipe
    from media_hub.snapshotter import _build_step_groups, _paginate_groups, MAX_STEPS_PER_PAGE
    
    recipe_id = request.args.get("id", type=int)
    if not recipe_id:
        return jsonify({"error": "No recipe ID"}), 400
    recipe = db.session.get(Recipe, recipe_id)
    if not recipe:
        return jsonify({"error": "Not found"}), 404
        
    step_groups = _build_step_groups(recipe)
    dynamic_steps = []
    
    for comp_idx, group in enumerate(step_groups, start=1):
        pages = _paginate_groups([group], MAX_STEPS_PER_PAGE)
        for p_idx, page_groups in enumerate(pages, start=1):
            dynamic_steps.append({
                "fragment_name": f"step{comp_idx}",
                "page": p_idx,
                "total_pages": len(pages),
                "component_name": group["component"]
            })
            
    return jsonify({"steps": dynamic_steps})

@media_hub_bp.route("/sandbox", methods=["GET"])
"""
content = content.replace('@media_hub_bp.route("/sandbox", methods=["GET"])', new_route)

with open(routes_file, "w") as f:
    f.write(content)
print("done")
