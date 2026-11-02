"""The weekly report on the TikTok and Instagram posts (docs/SOCIAL.md, "Learning from the posts"). The week's numbers
come from the post log (services/funnel.py); Claude reads them and says, in Norwegian, what won, what lost and the one
thing to change next. It is given numbers only and told not to judge on one post. Sunday morning the Cloud Scheduler job
social-report calls /internal/tasks/social-report, after social-stats has fetched Instagram's numbers; TikTok's are
what has been typed in. It lands on the Funnel page. One short Sonnet call, a few cents a week; a week with no posts
makes no call.
"""
import datetime
import json
import os
import statistics

from database.models import SocialReport, db
from services import ai_models, funnel
from services.recipe_v2 import claude

DAYS = 7
GROUP_DAYS = 28  # the groups look further back: one week is too few posts to judge a series on
PROMPT = os.path.join(os.path.dirname(__file__), '..', 'data', 'prompts', 'social', 'weekly_report.md')
SCHEMA = {
    'type': 'object', 'additionalProperties': False,
    'required': ['headline', 'won', 'lost', 'change', 'why', 'caution'],
    'properties': {
        'headline': {'type': 'string'},
        'won': {'type': 'array', 'items': {'type': 'string'}},
        'lost': {'type': 'array', 'items': {'type': 'string'}},
        'change': {'type': 'string'},
        'why': {'type': 'string'},
        'caution': {'type': 'string'},
    },
}


def _post(row, today):
    post, stat = row['post'], row['latest']
    numbers = {key: getattr(stat, key) if stat else None for key in funnel.STAT_FIELDS}
    return {'ref': row['ref'], 'platform': post.platform, 'went_up': post.posted_on.isoformat(),
            'days_up': (today - post.posted_on).days, 'title': post.title, 'series': post.series or post.format,
            'hook': post.hook, 'hook_group': post.hook_group, 'cta_group': post.cta_group, 'sound': post.sound,
            'notes': post.notes, 'numbers_from_day': stat.day if stat else None, **numbers,
            'visits': row['visits'], 'signups': row['signups'], 'made': row['made'], 'visits_1000': row['per_1000']}


def _totals(rows):
    seen = [r['latest'].views for r in rows if r['latest'] and r['latest'].views]
    return {'posts': len(rows), 'views': sum(seen), 'median_views': round(statistics.median(seen)) if seen else None,
            'visits': sum(r['visits'] for r in rows), 'signups': sum(r['signups'] for r in rows),
            'without_numbers': sum(1 for r in rows if not r['latest'])}


def facts(today=None):
    """What the report is written from, as plain data: this week's posts and last week's totals, the groups over the
    last four weeks, and how far the goal is. Drafts are left out."""
    today = today or datetime.date.today()
    report = funnel.report(today=today)
    posted = [r for r in report['posts'] if r['post'].status == 'posted']
    week = today - datetime.timedelta(days=DAYS)
    this = [r for r in posted if week < r['post'].posted_on <= today]
    last = [r for r in posted if week - datetime.timedelta(days=DAYS) < r['post'].posted_on <= week]
    return {'week_ending': today.isoformat(), 'posts': [_post(r, today) for r in this], 'this_week': _totals(this),
            'last_week': _totals(last), 'groups_28_days': funnel.summary(report['posts'], today, GROUP_DAYS),
            'goal': {'signups_wanted': 50, 'made_wanted': 10, 'before': '2027-01-31'}, 'users': report['totals']}


def read(data, call=None):
    """Claude's reading of the facts: {'headline', 'won', 'lost', 'change', 'why', 'caution'}."""
    call = call or claude.call
    with open(PROMPT, encoding='utf-8') as f:
        system = f.read()
    message, usage = call(ai_models.SOCIAL_REPORT_MODEL, ai_models.SOCIAL_REPORT_EFFORT,
                          [{'role': 'user', 'content': json.dumps(data, ensure_ascii=False)}], system=system,
                          schema=SCHEMA)
    print(f"social-report: {usage.get('cost_usd')} USD")
    return json.loads(claude.text_of(message))


def write_week(today=None, replace=False, call=None):
    """The report for the week ending today, kept per week; one already written is returned as it is unless replace."""
    today = today or datetime.date.today()
    row = db.session.execute(db.select(SocialReport).filter_by(week_ending=today)).scalar()
    if row and not replace:
        return row
    data = facts(today)
    report = read(data, call) if data['posts'] else {
        'headline': 'Ingen poster gikk ut denne uka.', 'won': [], 'lost': [], 'change': '', 'why': '', 'caution': ''}
    if row is None:
        row = SocialReport(week_ending=today, facts=data, report=report)
        db.session.add(row)
    else:
        row.facts, row.report, row.written_at = data, report, datetime.datetime.utcnow()
    db.session.commit()
    return row
