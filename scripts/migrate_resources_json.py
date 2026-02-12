import os
import json
import sys

# Add parent directory to path to import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from database.models import Resource

def migrate_resources():
    print("Starting Resource Migration...")
    
    data_path = os.path.join(app.root_path, 'data', 'resources.json')
    if not os.path.exists(data_path):
        print(f"Error: {data_path} not found.")
        return

    with open(data_path, 'r') as f:
        data = json.load(f)

    with app.app_context():
        # 1. Create Resources
        print("Creating entries...")
        slug_map = {}
        
        for item in data:
            slug = item.get('slug') or item.get('id')
            
            # Check if exists
            existing = db.session.execute(db.select(Resource).where(Resource.slug == slug)).scalar_one_or_none()
            if existing:
                print(f"Skipping existing: {slug}")
                slug_map[slug] = existing
                continue
            
            # Convert tags list to string
            tags_list = item.get('tags', [])
            tags_str = ",".join(tags_list) if isinstance(tags_list, list) else tags_list
            
            resource = Resource(
                slug=slug,
                title=item.get('title'),
                summary=item.get('summary'),
                content_markdown=item.get('content_markdown'),
                image_filename=item.get('image_filename'),
                tags=tags_str
            )
            
            db.session.add(resource)
            db.session.flush() # Get ID
            slug_map[slug] = resource
            print(f"Added: {slug}")
        
        db.session.commit()
        
        # 2. Link Relations
        print("Linking relations...")
        for item in data:
            slug = item.get('slug') or item.get('id')
            resource = slug_map.get(slug)
            
            if not resource:
                continue
                
            related_slugs = item.get('related_slugs', [])
            for r_slug in related_slugs:
                related = slug_map.get(r_slug)
                # If related not in current batch, try fetching from DB (if it was already there)
                if not related:
                     related = db.session.execute(db.select(Resource).where(Resource.slug == r_slug)).scalar_one_or_none()
                
                if related and related not in resource.related_resources:
                    resource.related_resources.append(related)
                    print(f"Linked {slug} -> {r_slug}")
        
        db.session.commit()
        print("Migration Complete!")

if __name__ == '__main__':
    migrate_resources()
