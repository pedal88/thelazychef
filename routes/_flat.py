"""Blueprint that keeps the endpoint names routes had when they lived in app.py.

A normal Blueprint registers its views as '<blueprint>.<function>', which would
break every url_for('recipes_list') in templates and code. FlatBlueprint
registers them under the bare function name instead, so routes can move out of
app.py without renaming anything.

Limits: url_prefix/subdomain are ignored, and blueprint-level hooks
(before_request, errorhandler, ...) don't run for these views, because Flask
matches those by the endpoint's blueprint prefix. Use a normal Blueprint for new
code that needs either.
"""
from flask import Blueprint


class FlatBlueprint(Blueprint):
    def add_url_rule(self, rule, endpoint=None, view_func=None,
                     provide_automatic_options=None, **options):
        if endpoint is None:
            endpoint = view_func.__name__

        def register(state):
            state.app.add_url_rule(rule, endpoint, view_func,
                                   provide_automatic_options=provide_automatic_options,
                                   **options)

        self.record(register)
