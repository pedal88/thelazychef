import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import app
from database.models import Resource

with app.app_context():
    r = Resource.query.filter_by(slug='intro-to-pans').first()
    if r:
        print("MARKDOWN_CONTENT_START")
        print(r.content_markdown)
        print("MARKDOWN_CONTENT_END")
    else:
        print("Resource not found")
