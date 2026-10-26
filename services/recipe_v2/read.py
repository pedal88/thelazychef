"""What the recipe page shows, derived from the graph and not stored.

shopping_list: every ingredient once, with the amounts summed per unit, and
where it is used. The same ingredient on two lines (garlic in the marinade and
in the sauce) is one entry, "used 2 times" (RECIPE_VISUALIZATIONS.md 9.15).
"""


def shopping_list(v2, factor=1.0):
    """Entries in the order the ingredients first appear.

    Lines are grouped by pantry id, or by name when the line has none. Amounts
    are summed per unit, since units are not converted yet. factor scales the
    amounts (servings wanted / servings in the recipe).
    """
    comps = {c['local_id']: c['name'] for c in v2.get('components') or []}
    entries = {}
    for line in v2.get('ingredients') or []:
        key = line.get('pantry_id') or (line.get('name') or '').strip().lower()
        e = entries.setdefault(key, {'name': line['name'], 'pantry_id': line.get('pantry_id'), 'amounts': {},
                                     'to_taste': False, 'parts': [], 'uses': 0, 'varieties': []})
        e['uses'] += 1
        if line.get('variety') and line['variety'] not in e['varieties']:  # what to buy: "melne" potatoes
            e['varieties'].append(line['variety'])
        part = comps.get(line.get('component_id'))
        if part and part not in e['parts']:
            e['parts'].append(part)
        if line.get('amount') is None:
            e['to_taste'] = True
        else:
            unit = line.get('unit') or 'piece'
            e['amounts'][unit] = e['amounts'].get(unit, 0) + line['amount'] * factor
    return [dict(e, amounts=[{'amount': a, 'unit': u} for u, a in e['amounts'].items()]) for e in entries.values()]
