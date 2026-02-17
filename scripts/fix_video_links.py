import sys
import os
import re

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, db
from database.models import Resource

def fix_video_links():
    with app.app_context():
        resources = Resource.query.all()
        count = 0
        for resource in resources:
            if resource.content_markdown:
                original = resource.content_markdown
                
                # Regex to find links to mp4: [text](url.mp4)
                # We want to change it to: ![](url.mp4)
                # Pattern: \[.*?\]\((.*?\.mp4)\)
                
                pattern = r'\[.*?\]\((.*?\.mp4)\)'
                
                if re.search(pattern, original):
                    print(f"Fixing Video Link in Resource ID {resource.id}: {resource.title}")
                    
                    # Replace with ![](\1)
                    # Note: We discard the link text text because video player doesn't need it
                    # or we could put it in alt text: ![\1](\2)
                    
                    new_content = re.sub(r'\[(.*?)\]\((.*?\.mp4)\)', r'![\1](\2)', original)
                    
                    resource.content_markdown = new_content
                    db.session.add(resource)
                    count += 1
        
        if count > 0:
            db.session.commit()
            print(f"Successfully converted {count} video links to images.")
        else:
            print("No video links found.")

if __name__ == "__main__":
    fix_video_links()
