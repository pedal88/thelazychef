from google.cloud import storage
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def make_bucket_public():
    bucket_name = "thelazychef-assets"
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)

        # Method 1: IAM Policy (Standard for Uniform Access)
        policy = bucket.get_iam_policy(requested_policy_version=3)
        policy.bindings.append(
            {"role": "roles/storage.objectViewer", "members": {"allUsers"}}
        )
        bucket.set_iam_policy(policy)
        
        logger.info(f"Bucket {bucket_name} is now public (IAM allUsers:objectViewer).")

    except Exception as e:
        logger.error(f"Error setting public access: {e}")

if __name__ == "__main__":
    make_bucket_public()
