import re

with open('templates/admin/recipes_management.html', 'r') as f:
    html = f.read()

# 1. Define the macro
macro_def = """
{% macro filterable_sortable_th(label, col_id, filter_param, options, selected_values, classes="") %}
<th scope="col" class="{{ classes }} relative group">
    <div class="flex items-center gap-1 h-full">
        <!-- Sortable Header Link -->
        {% set args = request.args.copy() %}
        {% set _ = args.update({'sort': col_id, 'dir': 'asc' if current_sort == col_id and current_dir == 'desc' else 'desc'}) %}
        
        <a href="?{{ urlencode(args) }}"
           class="inline-flex items-center flex-1 text-indigo-600 hover:text-indigo-900 focus:outline-none whitespace-nowrap">
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

        <!-- Filter Dropdown Icon -->
        {% if options %}
        <div class="relative inline-block text-left filter-dropdown-container group/filter">
            <button type="button" onclick="toggleFilterMenu('menu-{{ filter_param }}')"
                class="text-gray-400 hover:text-indigo-600 focus:outline-none">
                <svg class="h-4 w-4 {% if selected_values %}text-indigo-600{% endif %}" fill="none"
                    viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round"
                        d="M12 3c2.755 0 5.455.232 8.083.678.533.09.917.556.917 1.096v1.044a2.25 2.25 0 01-.659 1.591l-5.432 5.432a2.25 2.25 0 00-.659 1.591v2.927a2.25 2.25 0 01-1.244 2.013L9.75 21v-6.568a2.25 2.25 0 00-.659-1.591L3.659 7.409A2.25 2.25 0 013 5.818V4.774c0-.54.384-1.006.917-1.096A48.32 48.32 0 0112 3z" />
                </svg>
            </button>

            <div id="menu-{{ filter_param }}"
                class="hidden absolute left-0 z-20 mt-2 w-56 origin-top-left rounded-md bg-white shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none font-normal">
                <div class="p-2 border-b border-gray-100 flex justify-between text-xs font-semibold text-indigo-600 bg-gray-50 rounded-t-lg">
                    <span class="cursor-pointer hover:underline" onclick="selectAllFilters('{{ filter_param }}')">All</span>
                    <span class="cursor-pointer hover:underline" onclick="clearFilters('{{ filter_param }}')">None</span>
                </div>
                <div class="max-h-60 overflow-y-auto p-1 text-left">
                    {% for opt in options %}
                    <div class="flex items-center px-4 py-2 hover:bg-gray-50 focus-within:bg-gray-50">
                        <input type="checkbox" data-col="{{ filter_param }}" value="{{ opt }}" 
                            {% if opt in selected_values %}checked{% endif %}
                            class="filter-cb h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-600 cursor-pointer">
                        <label class="ml-3 block text-sm text-gray-700 whitespace-normal cursor-pointer w-full" onclick="this.previousElementSibling.click()">{{ opt }}</label>
                    </div>
                    {% endfor %}
                </div>
            </div>
        </div>
        {% endif %}
    </div>
</th>
{% endmacro %}
"""

if '{% macro filterable_sortable_th' not in html:
    html = html.replace('{% macro colored_score(score_val) %}', macro_def + '\n{% macro colored_score(score_val) %}')


# 2. Add Apply Filters button
action_bar_search = """
                <button id="apply-filters-btn" onclick="applyFilters()"
                    class="hidden inline-flex items-center gap-2 rounded-full bg-indigo-600 px-5 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 transition-colors">
                    Apply Filters
                </button>
            </div>
            
            <form method="GET" action="{{ url_for('admin_recipes_management') }}" class="w-full sm:w-72">
"""
html = re.sub(r'            </div>\s*<form method="GET"', action_bar_search, html)


# 3. Use the macro for headers.
# I will regex replace the old {{ sortable_th(...) }} calls for categorical columns with filterable_sortable_th
replacements = [
    (r"{{ sortable_th\('Cuisines', 'cuisine', 'col-cat py-3.5 px-3 text-left text-xs font-semibold text-gray-900'\) }}", 
     "{{ filterable_sortable_th('Cuisines', 'cuisine', 'cuisine', cuisine_options, selected_cuisines, 'col-cat py-3.5 px-3 text-left text-xs font-semibold text-gray-900') }}"),
    
    (r'<th scope="col"\s*class="col-cat py-3.5 px-3 text-left text-xs font-semibold text-gray-900">Diets\s*</th>', 
     "{{ filterable_sortable_th('Diets', 'none', 'diet', diet_options, selected_diets, 'col-cat py-3.5 px-3 text-left text-xs font-semibold text-gray-900') }}"),

    (r'<th scope="col"\s*class="col-cat py-3.5 px-3 text-left text-xs font-semibold text-gray-900">Meal\s*Type</th>',
     "{{ filterable_sortable_th('Meal Type', 'none', 'meal_type', meal_type_options, selected_meal_types, 'col-cat py-3.5 px-3 text-left text-xs font-semibold text-gray-900') }}"),

    (r'<th scope="col"\s*class="col-cat py-3.5 px-3 text-left text-xs font-semibold text-gray-900">Main\s*Protein</th>',
     "{{ filterable_sortable_th('Main Protein', 'none', 'protein', protein_options, selected_proteins, 'col-cat py-3.5 px-3 text-left text-xs font-semibold text-gray-900') }}"),

    (r"{{ sortable_th\('Difficulty', 'difficulty', 'col-cat py-3.5 px-3 text-left text-xs font-semibold text-gray-900'\) }}",
     "{{ filterable_sortable_th('Difficulty', 'difficulty', 'difficulty', difficulty_options, selected_difficulties, 'col-cat py-3.5 px-3 text-left text-xs font-semibold text-gray-900') }}"),

    (r'<th scope="col"\s*class="py-3.5 pl-4 pr-3 text-left text-xs font-semibold text-gray-900">Publish\s*Status</th>',
     "{{ filterable_sortable_th('Publish Status', 'status', 'status', status_options, selected_statuses, 'py-3.5 pl-4 pr-3 text-left text-xs font-semibold text-gray-900') }}")
]

for t_find, t_replace in replacements:
    html = re.sub(t_find, t_replace, html)

# 4. Integrate filter JS
js_logic = """
    // === Filters Logic ===
    function toggleFilterMenu(menuId) {
        document.querySelectorAll('[id^="menu-"]').forEach(el => {
            if (el.id !== menuId) el.classList.add('hidden');
        });
        document.getElementById(menuId).classList.toggle('hidden');
    }

    document.addEventListener('change', e => {
        if (e.target.classList.contains('filter-cb')) {
            document.getElementById('apply-filters-btn').classList.remove('hidden');
        }
    });

    function selectAllFilters(colId) {
        document.querySelectorAll(`input[data-col="${colId}"]`).forEach(i => i.checked = true);
        document.getElementById('apply-filters-btn').classList.remove('hidden');
    }

    function clearFilters(colId) {
        document.querySelectorAll(`input[data-col="${colId}"]`).forEach(i => i.checked = false);
        document.getElementById('apply-filters-btn').classList.remove('hidden');
    }

    function applyFilters() {
        const params = new URLSearchParams(window.location.search);
        
        // Remove all previous filter keys to overwrite them
        const filterKeys = ['cuisine', 'diet', 'meal_type', 'protein', 'difficulty', 'status'];
        filterKeys.forEach(k => params.delete(k));

        document.querySelectorAll('.filter-cb:checked').forEach(cb => {
            params.append(cb.dataset.col, cb.value);
        });

        // Reset page to 1 when filtering
        params.set('page', 1);

        window.location.search = params.toString();
    }

    document.addEventListener('click', e => {
        if (!e.target.closest('.filter-dropdown-container')) {
            document.querySelectorAll('[id^="menu-"]').forEach(el => el.classList.add('hidden'));
        }
    });

</script>
"""
html = html.replace('</script>\n{% endblock %}', js_logic + '\n{% endblock %}')

with open('templates/admin/recipes_management.html', 'w') as f:
    f.write(html)

