"""Answers in gzip when the browser takes it: neither gunicorn nor Cloud Run does it for us, and most visitors come on a
phone. Text only; images are compressed already. The standard library is enough, so no package to keep up to date."""
import gzip

from flask import request

TYPES = {'text/html', 'text/css', 'text/plain', 'text/javascript', 'application/javascript', 'application/json',
         'image/svg+xml'}
SMALLEST = 1024  # below this the saving is too small to bother


def compress(response):
    """An after_request. Register it before the others, since Flask runs them last first and this must see the final body."""
    response.vary.add('Accept-Encoding')
    if (request.method == 'HEAD' or response.status_code != 200 or response.mimetype not in TYPES
            or response.is_streamed and not response.direct_passthrough or 'Content-Encoding' in response.headers
            or 'gzip' not in request.headers.get('Accept-Encoding', '')):
        return response
    response.direct_passthrough = False  # a static file: read it here
    body = response.get_data()
    if len(body) < SMALLEST:
        return response
    response.set_data(gzip.compress(body, compresslevel=6, mtime=0))
    response.headers['Content-Encoding'] = 'gzip'
    return response
