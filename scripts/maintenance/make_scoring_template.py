import re

with open('templates/recipes_table.html', 'r') as f:
    html = f.read()

# Update titles and form action
html = html.replace("url_for('recipes_table_view')", "url_for('recipe_scoring_view')")
html = html.replace("Recipes Table - The Lazy Chef", "Recipe QA Scoring - The Lazy Chef")
html = html.replace("Recipes Database", "Recipe QA Scoring")
html = html.replace("A detailed view of all recipes including nutritional data.", "A detailed view of recipe quality metrics from the LLM-as-a-Judge pipeline.")

# The headers to remove: Cuisine, Diet, Meal Type, Protein, Difficulty, Nutrition X 6
# Let's target the exact block in the thead:
header_target = """                                    {{ header_cell('cuisine', 'Cuisine', cuisine_options, selected_cuisines) }}
                                    {{ header_cell('diet', 'Diet', diet_options, selected_diets) }}
                                    {{ header_cell('meal_type', 'Meal Type', meal_type_options, selected_meal_types) }}
                                    {{ header_cell('protein_type', 'Protein', protein_options, selected_proteins) }}
                                    {{ header_cell('difficulty', 'Difficulty', difficulty_options,
                                    selected_difficulties) }}

                                    <!-- Nutrition -->
                                    {{ header_cell('total_calories', 'Kcal') }}
                                    {{ header_cell('total_protein', 'Prot (g)') }}
                                    {{ header_cell('total_carbs', 'Carbs (g)') }}
                                    {{ header_cell('total_fat', 'Fat (g)') }}
                                    {{ header_cell('total_fiber', 'Fiber (g)') }}
                                    {{ header_cell('total_sugar', 'Sugar (g)') }}"""

new_headers = """                                    {{ header_cell('total_score', 'Total Score') }}
                                    {{ header_cell('score_name', 'Name Fit') }}
                                    {{ header_cell('score_ingredients', 'Ingredient Match') }}
                                    {{ header_cell('score_components', 'Components') }}
                                    {{ header_cell('score_amounts', 'Amounts') }}
                                    {{ header_cell('score_steps', 'Steps Clarity') }}"""

# Normalize spaces to make naive replace work, or use regex
import re
# Just fallback to generic split if direct replacement fails. We'll manually specify columns to build the new tbody and thead.
# Actually, the user asked for very specific columns, so I'll just write the entire <thead> and <tbody> manually using python string formatting to be safe.

header_pattern = re.compile(r"\{\{ header_cell\('cuisine'.*?total_sugar', 'Sugar \(g\)'\) \}\}", re.DOTALL)
html = header_pattern.sub(new_headers, html)

data_pattern = re.compile(r"<!-- Categorical Data -->.*?recipe.total_sugar\|default\('-', true\) \}\}<\/td>", re.DOTALL)
new_cells = """<!-- QA Score Data -->
                                    <td class="whitespace-nowrap px-3 py-4 text-sm font-bold {% if recipe.evaluation and recipe.evaluation.total_score < 50 %}text-red-600{% elif recipe.evaluation %}text-green-600{% else %}text-gray-500{% endif %}">
                                        {{ recipe.evaluation.total_score|round(1) if recipe.evaluation else '-' }}
                                    </td>
                                    <td class="whitespace-nowrap px-3 py-4 text-sm text-gray-500">
                                        {{ recipe.evaluation.score_name if recipe.evaluation else '-' }}
                                    </td>
                                    <td class="whitespace-nowrap px-3 py-4 text-sm text-gray-500">
                                        {{ recipe.evaluation.score_ingredients if recipe.evaluation else '-' }}
                                    </td>
                                    <td class="whitespace-nowrap px-3 py-4 text-sm text-gray-500">
                                        {{ recipe.evaluation.score_components if recipe.evaluation else '-' }}
                                    </td>
                                    <td class="whitespace-nowrap px-3 py-4 text-sm text-gray-500">
                                        {{ recipe.evaluation.score_amounts if recipe.evaluation else '-' }}
                                    </td>
                                    <td class="whitespace-nowrap px-3 py-4 text-sm text-gray-500">
                                        {{ recipe.evaluation.score_steps if recipe.evaluation else '-' }}
                                    </td>"""

html = data_pattern.sub(new_cells, html)

# The Actions header was before Categorical Data in thead and tbody. Let's make sure it's kept intact.
with open('templates/recipes_scoring_table.html', 'w') as f:
    f.write(html)

print("Template written!")
