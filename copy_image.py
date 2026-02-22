import os
from database.models import db, Recipe
from app import app

app.app_context().push()
storage_backend = os.getenv("STORAGE_BACKEND", "local")

recipe147 = db.session.get(Recipe, 147)
recipe148 = db.session.get(Recipe, 148)

if storage_backend == "gcs":
    # Get image file names
    if recipe147 and recipe148:
        # Just update the image_filename
        recipe147.image_filename = recipe148.image_filename
        db.session.commit()
        print("Successfully copied image from recipe 148 to 147 (DB update only)")
    else:
        print("One or both recipes not found")
else:
    print("GCS not enabled. Please enable GCS")