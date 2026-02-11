from google.cloud import storage
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_bucket():
    bucket_name = "thelazychef-assets"
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        bucket.storage_class = "STANDARD"
        
        # Check if exists
        if bucket.exists():
            logger.info(f"Bucket {bucket_name} already exists.")
            return

        # Create
        logger.info(f"Creating bucket {bucket_name} in europe-west1...")
        new_bucket = storage_client.create_bucket(bucket_name, location="europe-west1")
        logger.info(f"Created bucket {new_bucket.name} in {new_bucket.location}")

    except Exception as e:
        logger.error(f"Error creating bucket: {e}")

if __name__ == "__main__":
    create_bucket()
