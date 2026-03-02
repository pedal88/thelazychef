import re

content = open('templates/admin/recipes_management.html', 'r').read()

# Add search bar
search_html = """
        <!-- Action Bar -->
        <div class="mt-4 flex flex-wrap items-center gap-3 justify-between">
            <div class="flex flex-wrap items-center gap-3">
                <button id="score-selected-btn"
                    class="inline-flex items-center rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50"
                    onclick="bulkScoreSelected()">Score Selected</button>
                <button id="score-all-btn"
                    class="inline-flex items-center rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50"
                    onclick="bulkScoreAll()">Score All Unscored</button>
                <button id="delete-selected-btn"
                    class="inline-flex items-center rounded-md px-3 py-2 text-sm font-semibold text-red-600 shadow-sm ring-1 ring-inset ring-red-300 hover:bg-red-50"
                    onclick="bulkDeleteAdmin()">Delete Selected</button>
            </div>
            
            <div class="relative w-full sm:w-64 mt-2 sm:mt-0">
                <input type="text" id="recipeSearch" placeholder="Filter / Search recipes..." 
                    class="block w-full rounded-md border-0 py-1.5 px-3 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-indigo-600 sm:text-sm sm:leading-6">
            </div>
        </div>
"""
content = re.sub(r'<!-- Action Bar -->.*?</div>\s*</div>', search_html, content, flags=re.DOTALL) # Wait! Let's just string replace the action bar block

with open('templates/admin/recipes_management.html', 'w') as f:
    f.write(content)

