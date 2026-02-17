import sys
import os
import re

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, db
from database.models import Resource

def fix_urls():
    with app.app_context():
        resources = Resource.query.all()
        count = 0
        for resource in resources:
            if resource.content_markdown:
                original_content = resource.content_markdown
                
                # Regex to find: http://127.0.0.1:8000/(https?://...)
                # We'll use a broader pattern to catch localhost IPs or just the double http
                # Pattern: Any URL that ends with another http(s):// inside it
                
                # Specifically targeting the reported issue:
                # http://127.0.0.1:8000/https://storage.googleapis.com
                
                pattern = r'http://127\.0\.0\.1:8000/(https?://)'
                
                if re.search(pattern, original_content):
                    print(f"Fixing Resource ID {resource.id}: {resource.title}")
                    
                    # Replace
                    new_content = re.sub(pattern, r'\1', original_content)
                    
                    # Also check for other double http patterns just in case? 
                    # generic: content.replace("http://127.0.0.1:8000/http", "http") is safer if we know exact prefix
                    
                    resource.content_markdown = new_content
                    db.session.add(resource)
                    count += 1
        
        if count > 0:
            db.session.commit()
            print(f"Successfully fixed {count} resources.")
        else:
            print("No resources found with malformed URLs.")

if __name__ == "__main__":
    fix_urls()
