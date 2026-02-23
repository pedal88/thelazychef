content = open('templates/admin/recipes_management.html', 'r').read()

import re

# Checkbox
content = content.replace('<th scope="col" class="relative px-3 sm:w-12 sm:px-6">', '<th scope="col" class="relative px-3 sm:w-12 sm:px-6 no-sort" data-sort-method="none">')
# Image
content = content.replace('<th scope="col"\n                                        class="py-3.5 pl-4 pr-3 text-left text-xs font-semibold text-gray-900 sm:pl-6">\n                                        Image</th>', '<th scope="col" data-sort-method="none"\n                                        class="py-3.5 pl-4 pr-3 text-left text-xs font-semibold text-gray-900 sm:pl-6 no-sort">\n                                        Image</th>')
# Actions
content = content.replace('<th scope="col" class="py-3.5 px-3 text-left text-xs font-semibold text-gray-900">\n                                        Actions</th>', '<th scope="col" data-sort-method="none" class="py-3.5 px-3 text-left text-xs font-semibold text-gray-900 no-sort">\n                                        Actions</th>')

with open('templates/admin/recipes_management.html', 'w') as f:
    f.write(content)
