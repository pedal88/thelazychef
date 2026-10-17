from google import genai
import os
try:
    client = genai.Client(project=os.getenv("GOOGLE_CLOUD_PROJECT", "your-project-id"), location=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"))
    for m in client.models.list():
        if "imagen" in m.name:
            print(m.name)
except Exception as e:
    print(f"Error: {e}")
