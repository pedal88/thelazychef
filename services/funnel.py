"""Where users come from, for the TikTok and Instagram funnel (routes/funnel_routes.py).

A visit can bring a ref code: the short addresses (thelazychef.app/tiktok, /ig, and /tiktok/3, which gives tiktok-3 so
one post can be told from another) or ?ref= on any page. The first code of a browser session is kept in the session and
counted per day (ReferralVisit); when the visitor signs up, it is saved on the user with their answer to "How did you
find us?". The admin Funnel page counts sign-ups and the users who saved or made a recipe, per channel and week.
"""
import datetime
import re

from flask import session
from sqlalchemy import case, func

from database.models import ReferralVisit, User, UserRecipeInteraction, db

# The answers to "How did you find us?" on the sign-up form: (stored value, label)
SOURCES = [
    ('tiktok', 'TikTok'),
    ('instagram', 'Instagram'),
    ('search', 'Google or another search'),
    ('friend', 'A friend'),
    ('other', 'Somewhere else'),
]

# A ref code's first word and the channel it belongs to (ig-3 and instagram-reel-2 are both Instagram)
_CHANNEL_OF_REF = {'tiktok': 'tiktok', 'tt': 'tiktok', 'ig': 'instagram', 'instagram': 'instagram'}

CHANNELS = [value for value, _ in SOURCES] + ['unknown']
CHANNEL_LABELS = dict(SOURCES, unknown='Not known')

SESSION_KEY = 'ref'


def clean_ref(value):
    """A ref code as stored: lower case, letters, digits, - and _, at most 60 characters; None when nothing is left."""
    ref = re.sub(r'[^a-z0-9_-]+', '', (value or '').strip().lower())[:60]
    return ref or None


def remember(ref):
    """Keeps the first ref code of this browser session and counts the visit. Later codes are ignored, so a visitor who
    came from TikTok and then opens a shared ?ref=ig link stays a TikTok visitor."""
    ref = clean_ref(ref)
    if not ref or session.get(SESSION_KEY):
        return
    session[SESSION_KEY] = ref
    today = datetime.date.today()
    visit = db.session.execute(db.select(ReferralVisit).filter_by(ref=ref, day=today)).scalar()
    if visit is None:
        visit = ReferralVisit(ref=ref, day=today, count=0)
        db.session.add(visit)
    visit.count += 1
    db.session.commit()


def session_ref():
    return session.get(SESSION_KEY)


def channel(user):
    """The channel a user came through: their ref code first (it is measured), then their answer, else 'unknown'."""
    if user.signup_ref:
        first = user.signup_ref.split('-', 1)[0].split('_', 1)[0]
        if first in _CHANNEL_OF_REF:
            return _CHANNEL_OF_REF[first]
    if user.signup_source in CHANNEL_LABELS:
        return user.signup_source
    return 'unknown'


def _monday(day):
    return day - datetime.timedelta(days=day.weekday())


def report(weeks=12, today=None):
    """The numbers on the Funnel page. Admins are left out. Users from before the tracking (no created_at) count in the
    totals but not in any week.

    {'weeks': [{'start', 'signups': {channel: n}, 'total'}], newest first,
     'channels': [{'key', 'label', 'signups', 'saved', 'made'}],
     'totals': {'signups', 'saved', 'made', 'untracked'},
     'refs': [{'ref', 'visits', 'visits_28', 'signups', 'made'}], most visits first}"""
    today = today or datetime.date.today()
    users = db.session.execute(db.select(User).where(User.is_admin.is_not(True))).scalars().all()
    saved_ids = set(db.session.execute(
        db.select(UserRecipeInteraction.user_id).where(UserRecipeInteraction.status == 'favorite')).scalars())
    made_ids = set(db.session.execute(
        db.select(UserRecipeInteraction.user_id).where(
            (UserRecipeInteraction.is_made.is_(True)) | (UserRecipeInteraction.made_count > 0))).scalars())

    this_week = _monday(today)
    starts = [this_week - datetime.timedelta(weeks=i) for i in range(weeks)]
    by_week = {start: {key: 0 for key in CHANNELS} for start in starts}
    by_channel = {key: {'signups': 0, 'saved': 0, 'made': 0} for key in CHANNELS}
    by_ref = {}
    for user in users:
        key = channel(user)
        by_channel[key]['signups'] += 1
        by_channel[key]['saved'] += user.id in saved_ids
        by_channel[key]['made'] += user.id in made_ids
        if user.created_at:
            start = _monday(user.created_at.date())
            if start in by_week:
                by_week[start][key] += 1
        if user.signup_ref:
            row = by_ref.setdefault(user.signup_ref, {'signups': 0, 'made': 0})
            row['signups'] += 1
            row['made'] += user.id in made_ids

    since = today - datetime.timedelta(days=27)
    visits = db.session.execute(
        db.select(ReferralVisit.ref, func.sum(ReferralVisit.count),
                  func.sum(case((ReferralVisit.day >= since, ReferralVisit.count), else_=0)))
        .group_by(ReferralVisit.ref)).all()
    refs = {ref: {'ref': ref, 'visits': int(total or 0), 'visits_28': int(recent or 0), 'signups': 0, 'made': 0}
            for ref, total, recent in visits}
    for ref, row in by_ref.items():
        refs.setdefault(ref, {'ref': ref, 'visits': 0, 'visits_28': 0, 'signups': 0, 'made': 0}).update(row)

    return {
        'weeks': [{'start': start, 'signups': by_week[start], 'total': sum(by_week[start].values())}
                  for start in starts],
        'channels': [{'key': key, 'label': CHANNEL_LABELS[key], **by_channel[key]} for key in CHANNELS],
        'totals': {'signups': len(users), 'saved': len(saved_ids & {u.id for u in users}),
                   'made': len(made_ids & {u.id for u in users}),
                   'untracked': sum(1 for u in users if not u.created_at)},
        'refs': sorted(refs.values(), key=lambda r: (-r['visits'], -r['signups'], r['ref'])),
    }
