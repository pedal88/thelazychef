"""Smoke tests: pages load, and protected routes reject the wrong users.

Routes are discovered from app.url_map, so new routes are covered
automatically. Admin-only routes are detected by the @admin_required
decorator, so forgetting it on a new write endpoint fails
test_anonymous_cannot_call_write_endpoints.
"""
import os
import sys
import unittest

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Must be set before app is imported: in-memory DB, local storage, no real keys needed
os.environ['DB_BACKEND'] = 'local'
os.environ['DATABASE_URL'] = 'sqlite://'
os.environ['STORAGE_BACKEND'] = 'local'
os.environ.setdefault('SECRET_KEY', 'test-secret')
os.environ.setdefault('GOOGLE_API_KEY', 'test-key')
os.environ.pop('K_SERVICE', None)

from app import app  # noqa: E402
from database.models import db, User  # noqa: E402

WRITE_METHODS = {'POST', 'PUT', 'PATCH', 'DELETE'}

# Write endpoints that are intentionally open to anonymous users
PUBLIC_WRITE_ENDPOINTS = {
    'login',
    'register',
    'search_ingredients_api',  # read-only search that happens to use POST
}


def _decorators(view):
    """Qualified names of every wrapper around a view function."""
    names = []
    while view is not None:
        names.append(getattr(view, '__qualname__', ''))
        view = getattr(view, '__wrapped__', None)
    return names


def _has(view, decorator):
    return any(name.startswith(decorator + '.') for name in _decorators(view))


def _build_url(rule):
    """Fill URL parameters with dummy values (1 for ints, 'x' otherwise)."""
    values = {}
    for arg in rule.arguments:
        converter = rule._converters.get(arg)
        values[arg] = 1 if type(converter).__name__ == 'IntegerConverter' else 'x'
    with app.test_request_context():
        from flask import url_for
        return url_for(rule.endpoint, **values)


def _rules():
    return [r for r in app.url_map.iter_rules() if r.endpoint != 'static']


class SmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config['TESTING'] = True
        with app.app_context():
            db.create_all()
            for email, is_admin in (('admin@test', True), ('user@test', False)):
                user = User(email=email, is_admin=is_admin)
                user.set_password('pw')
                db.session.add(user)
            db.session.commit()
            cls.admin_id = db.session.execute(db.select(User.id).where(User.email == 'admin@test')).scalar()
            cls.user_id = db.session.execute(db.select(User.id).where(User.email == 'user@test')).scalar()

    def _client(self, user_id=None):
        client = app.test_client()
        if user_id is not None:
            with client.session_transaction() as session:
                session['_user_id'] = str(user_id)
                session['_fresh'] = True
        return client

    def test_admin_routes_are_discovered(self):
        # Guards against the decorator detection silently matching nothing
        admin_endpoints = [r for r in _rules() if _has(app.view_functions[r.endpoint], 'admin_required')]
        self.assertGreater(len(admin_endpoints), 20)

    def test_anonymous_cannot_call_write_endpoints(self):
        client = self._client()
        for rule in _rules():
            if rule.endpoint in PUBLIC_WRITE_ENDPOINTS:
                continue
            url = _build_url(rule)
            for method in sorted(rule.methods & WRITE_METHODS):
                with self.subTest(endpoint=rule.endpoint, method=method, url=url):
                    response = client.open(url, method=method)
                    self.assertIn(response.status_code, (302, 401, 403),
                                  f"{method} {url} is reachable without logging in")

    def test_regular_user_cannot_call_admin_routes(self):
        client = self._client(self.user_id)
        for rule in _rules():
            if not _has(app.view_functions[rule.endpoint], 'admin_required'):
                continue
            url = _build_url(rule)
            for method in sorted(rule.methods - {'HEAD', 'OPTIONS'}):
                with self.subTest(endpoint=rule.endpoint, method=method, url=url):
                    response = client.open(url, method=method)
                    self.assertEqual(response.status_code, 403,
                                     f"{method} {url} is reachable by a non-admin user")

    def test_public_pages_load(self):
        client = self._client()
        for rule in _rules():
            view = app.view_functions[rule.endpoint]
            if rule.arguments or 'GET' not in rule.methods:
                continue
            if _has(view, 'login_required') or _has(view, 'admin_required'):
                continue
            with self.subTest(endpoint=rule.endpoint, url=rule.rule):
                response = client.get(rule.rule)
                self.assertLess(response.status_code, 500, f"GET {rule.rule} crashed")

    def test_admin_pages_load(self):
        client = self._client(self.admin_id)
        for rule in _rules():
            view = app.view_functions[rule.endpoint]
            if rule.arguments or 'GET' not in rule.methods or not _has(view, 'admin_required'):
                continue
            with self.subTest(endpoint=rule.endpoint, url=rule.rule):
                response = client.get(rule.rule)
                self.assertLess(response.status_code, 500, f"GET {rule.rule} crashed for admin")


if __name__ == '__main__':
    unittest.main()
