"""Signing in with Google: OpenID Connect's authorization code flow, with no client library beyond google-auth.

Continue with Google on sign up and log in (templates/components/google_button.html) goes to Google
(/login/google, routes/auth_routes.py), which sends the visitor back to /login/google/done with a code. The code is
traded for an ID token, the token is checked (signed by Google, for this app, the email verified), and the user is
found by their Google account, else by their email, which Google has checked, else made. Off until
GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET are set (docs/SERVICES_AND_COSTS.md).

Google refuses to sign anyone in inside the browsers built into apps (Instagram, TikTok, Facebook), so there the button
gives way to a line asking to open the page in Safari or Chrome (in_app_browser). People who type the address from a
post are in their own browser; the Instagram bio link opens Instagram's."""
import os
import re
import secrets
from urllib.parse import urlencode

import requests
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from sqlalchemy import func

from database.models import User, db

AUTH_URL = 'https://accounts.google.com/o/oauth2/v2/auth'
TOKEN_URL = 'https://oauth2.googleapis.com/token'

# The browsers built into apps, by what they add to the user agent
_IN_APP = re.compile(r'Instagram|FBAN|FBAV|FB_IAB|musical_ly|BytedanceWebview|TikTok|Snapchat|LinkedInApp')


def client_id():
    return os.environ.get('GOOGLE_OAUTH_CLIENT_ID')


def enabled():
    return bool(client_id() and os.environ.get('GOOGLE_OAUTH_CLIENT_SECRET'))


def in_app_browser(user_agent):
    return bool(_IN_APP.search(user_agent or ''))


def start_url(redirect_uri, state):
    """Google's sign-in page for this app, asking only for who they are and their email."""
    return AUTH_URL + '?' + urlencode({'client_id': client_id(), 'redirect_uri': redirect_uri, 'response_type': 'code',
                                       'scope': 'openid email', 'state': state, 'prompt': 'select_account'})


def identity(code, redirect_uri):
    """(sub, email) for the code Google sent back, or None when the code or the token is no good or Google has not
    verified the email."""
    try:
        resp = requests.post(TOKEN_URL, timeout=10, data={
            'code': code, 'client_id': client_id(), 'client_secret': os.environ.get('GOOGLE_OAUTH_CLIENT_SECRET'),
            'redirect_uri': redirect_uri, 'grant_type': 'authorization_code'})
    except requests.RequestException:
        return None
    token = resp.json().get('id_token') if resp.ok else None
    if not token:
        return None
    try:
        claims = id_token.verify_oauth2_token(token, google_requests.Request(), client_id())
    except ValueError:
        return None
    email = (claims.get('email') or '').strip().lower()
    if not claims.get('sub') or not email or not claims.get('email_verified'):
        return None
    return claims['sub'], email


def user_for(sub, email, ref=None):
    """The user for a Google account: (user, made), where made says the account is new. A user who signed up with the
    same email and a password is the same person (Google has verified the email) and gets the Google account added.
    A new user gets a random password they never see, so the account has one like every other."""
    user = db.session.execute(db.select(User).where(User.google_sub == sub)).scalar()
    made = False
    if user is None:
        user = db.session.execute(db.select(User).where(func.lower(User.email) == email)).scalar()
        if user is None:
            user = User(email=email, is_admin=False, signup_ref=ref)
            user.set_password(secrets.token_urlsafe(32))
            db.session.add(user)
            made = True
        user.google_sub = sub
        db.session.commit()
    return user, made
