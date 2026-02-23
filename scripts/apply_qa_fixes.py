import re

with open('templates/admin/recipes_management.html', 'r') as f:
    content = f.read()

# 1. Inject macro after imports
macro = """
{% macro colored_score(score_val) %}
  {% if score_val and score_val != '-' and score_val != 'None' %}
    {% set s = score_val | float | int %}
    <span class="inline-flex items-center rounded-md px-2 py-1 text-xs font-medium ring-1 ring-inset
        {% if s < 80 %}bg-red-50 text-red-700 ring-red-600/10
        {% elif s <= 90 %}bg-orange-50 text-orange-700 ring-orange-600/20
        {% else %}bg-green-50 text-green-700 ring-green-600/20{% endif %}">
      {{ s }}
    </span>
  {% else %}
    -
  {% endif %}
{% endmacro %}
"""
if '{% macro colored_score' not in content:
    content = content.replace('{% import "components/modals/recipe_inspector.html" as inspector %}', 
                              '{% import "components/modals/recipe_inspector.html" as inspector %}\n' + macro)

# 2. Fix Categorization view QA score styling and round
# Replace yellow-50 with orange-50 etc.
content = content.replace('{% elif recipe.evaluation.total_score <= 90 %}bg-yellow-50 text-yellow-800 ring-yellow-600/20',
                          '{% elif recipe.evaluation.total_score|int <= 90 %}bg-orange-50 text-orange-700 ring-orange-600/20')
content = content.replace('{% if recipe.evaluation.total_score < 80 %}',
                          '{% if recipe.evaluation.total_score|int < 80 %}')

# round it
content = content.replace('{{ recipe.evaluation.total_score }}', '{{ recipe.evaluation.total_score | int }}')

# 3. Apply macro to all qa columns
cols = ['score_name', 'score_ingredients', 'score_components', 'score_amounts', 'score_steps', 'score_image']
for col in cols:
    target = f"recipe.evaluation.{col} if recipe.evaluation else '-'"
    if f"colored_score({target})" not in content:
        content = content.replace(target, f"colored_score(recipe.evaluation.{col}) if recipe.evaluation else '-'")

with open('templates/admin/recipes_management.html', 'w') as f:
    f.write(content)
