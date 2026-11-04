"""The switch in the admin chip: see the site as an admin, a signed-in user or a visitor (services/view_as.py)."""
from functools import wraps

from flask import Blueprint, abort, current_app, redirect, request, session, url_for
from werkzeug.exceptions import HTTPException

from services import signup, view_as
from services.view_as import ViewOnly

view_as_bp = Blueprint('view_as', __name__)


def account_admin_required(f):
    """admin_required for the account behind the session, so the way back works when the app sees a visitor."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = view_as.account()
        if user is None or not user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


def _admin_only(path):
    try:
        endpoint, _ = current_app.url_map.bind_to_environ(request.environ).match(path.split('?')[0], method='GET')
    except HTTPException:
        return False
    return getattr(current_app.view_functions[endpoint], 'admin_only', False)


@view_as_bp.route('/view-as', methods=['POST'])
@account_admin_required
def switch():
    """Back to the same page, or home when the page is for admins and the new role would only be refused it."""
    chosen = request.form.get('role')
    if chosen == 'admin':
        session.pop(view_as.KEY, None)
    elif chosen in view_as.ROLES:
        session[view_as.KEY] = chosen
    else:
        abort(400)
    back = signup.safe_next(request.form.get('next')) or url_for('content.home')
    return redirect(url_for('content.home') if chosen != 'admin' and _admin_only(back) else back)


@view_as_bp.app_errorhandler(ViewOnly)
def stopped(error):
    return view_as.refusal()
