"""A new password for someone who forgot theirs and wrote in (the log-in page says Email us; the site sends no email).

Only answer an email that comes from the address on the account. Without --apply nothing is saved: it says whether the
account exists and how it signs in. With --apply it sets a new random password and prints it to send them. Costs nothing.

    SSL_CERT_FILE=... DB_PASS=... DB_BACKEND=cloudsql ... ./venv/bin/python -m scripts.set_password --email someone@example.com
    ... -m scripts.set_password --email someone@example.com --apply
"""
import argparse
import getpass
import os
import secrets


def set_password(email, apply=False):
    """(user, the new password or None). The email is matched as logging in matches it, whatever its case."""
    from sqlalchemy import func

    from database.models import User, db

    user = db.session.execute(db.select(User).where(func.lower(User.email) == email.strip().lower())).scalar()
    if not user or not apply:
        return user, None
    password = secrets.token_urlsafe(9)
    user.set_password(password)
    db.session.commit()
    return user, password


def main():
    ap = argparse.ArgumentParser(description='A new password for someone who forgot theirs.')
    ap.add_argument('--email', required=True)
    ap.add_argument('--apply', action='store_true', help='set it; without it nothing is saved')
    args = ap.parse_args()
    if os.environ.get('DB_BACKEND') == 'cloudsql' and not os.environ.get('DB_PASS'):
        os.environ['DB_PASS'] = getpass.getpass('DB_PASS: ')

    from app import app

    with app.app_context():
        user, password = set_password(args.email, args.apply)
        if not user:
            print(f'No account with the email {args.email}.')
        elif password:
            print(f'New password for {user.email}: {password}')
        else:
            print(f'{user.email} exists{", and also signs in with Google" if user.google_sub else ""}. Nothing saved: add --apply.')


if __name__ == '__main__':
    main()
