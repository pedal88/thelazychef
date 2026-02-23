import re

with open('templates/admin/recipes_management.html', 'r') as f:
    html = f.read()

# 1. Add sortable_th macro
macro_def = """
{% macro sortable_th(label, col_id, classes="") %}
<th scope="col" class="{{ classes }}">
    <a href="?search={{ current_search }}&sort={{ col_id }}&dir={% if current_sort == col_id and current_dir == 'desc' %}asc{% else %}desc{% endif %}"
       class="group inline-flex items-center space-x-1 w-full h-full text-indigo-600 hover:text-indigo-900 focus:outline-none">
        <span>{{ label }}</span>
        <span class="ml-1 flex-none rounded text-gray-400 group-hover:bg-gray-200">
            {% if current_sort == col_id %}
                {% if current_dir == 'asc' %}
                <svg class="h-4 w-4 text-indigo-600" viewBox="0 0 20 20" fill="currentColor">
                    <path fill-rule="evenodd" d="M14.707 12.707a1 1 0 01-1.414 0L10 9.414l-3.293 3.293a1 1 0 01-1.414-1.414l4-4a1 1 0 011.414 0l4 4a1 1 0 010 1.414z" clip-rule="evenodd" />
                </svg>
                {% else %}
                <svg class="h-4 w-4 text-indigo-600" viewBox="0 0 20 20" fill="currentColor">
                    <path fill-rule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clip-rule="evenodd" />
                </svg>
                {% endif %}
            {% else %}
                <!-- Inactive sort icon -->
                <svg class="h-4 w-4 text-gray-400 opacity-0 group-hover:opacity-100" viewBox="0 0 20 20" fill="currentColor">
                    <path fill-rule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clip-rule="evenodd" />
                </svg>
            {% endif %}
        </span>
    </a>
</th>
{% endmacro %}
"""

if '{% macro sortable_th' not in html:
    html = html.replace('{% macro colored_score(score_val) %}', macro_def + '\n{% macro colored_score(score_val) %}')

# 2. Fix the search bar form
search_form = """
            <form method="GET" action="{{ url_for('admin_recipes_management') }}" class="w-full sm:w-72">
                <input type="hidden" name="sort" value="{{ current_sort }}">
                <input type="hidden" name="dir" value="{{ current_dir }}">
                <input type="text" name="search" id="recipeSearch" value="{{ current_search }}" placeholder="Search recipes (press Enter)..."
                    class="block w-full rounded-md border-0 py-1.5 px-3 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-indigo-600 sm:text-sm sm:leading-6">
            </form>
"""
html = re.sub(r'<div class="w-full sm:w-72">\s*<input type="text" id="recipeSearch" .*?</div>', search_form, html, flags=re.DOTALL)

# 3. Use the macro for all headers
# Name
html = re.sub(r'<th scope="col"\s*class="py-3.5 pl-4 pr-3 text-left text-xs font-semibold text-gray-900">Name</th>', 
              "{{ sortable_th('Name', 'title', 'py-3.5 pl-4 pr-3 text-left text-xs font-semibold text-gray-900') }}", html)

# Generic replace mapping (label, col_id, classes)
cols_map = {
    'Cuisines': 'cuisine',
    'Difficulty': 'difficulty',
    'QA Score': 'total_score',
    'Name Fit': 'score_name',
    'Ing. Match': 'score_ingredients',
    'Components': 'score_components',
    'Amounts': 'score_amounts',
    'Steps': 'score_steps',
    'Calories': 'total_calories',
    'Protein (g)': 'total_protein',
    'Fat (g)': 'total_fat',
    'Carbs (g)': 'total_carbs'
}

for label, col_id in cols_map.items():
    # Find existing header logic and replace with macro
    # E.g. <th scope="col" class="col-cat py-3.5 px-3 text-left text-xs font-semibold text-gray-900">Cuisines</th>
    # We will just replace it if we find the text
    pattern = r'<th scope="col"([^>]*)>\s*' + re.escape(label) + r'\s*</th>'
    
    def replacer(match):
        classes_str = match.group(1).replace('\n', ' ').strip()
        # extract just the class string if it exists
        c_match = re.search(r'class="([^"]+)"', classes_str)
        if c_match:
            cls = c_match.group(1)
        else:
            cls = ""
        return f"{{{{ sortable_th('{label}', '{col_id}', '{cls}') }}}}"

    html = re.sub(pattern, replacer, html)


# 4. Remove tablesort js entirely since we use server-side sorting now
html = re.sub(r'<script src="https://cdnjs.cloudflare.com/ajax/libs/tablesort/5.2.1/tablesort.min.js"></script>.*?</script>', '', html, flags=re.DOTALL)

with open('templates/admin/recipes_management.html', 'w') as f:
    f.write(html)
