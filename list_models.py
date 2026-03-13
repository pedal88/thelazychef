from google import genai
import os

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY", ""))

try:
    for m in client.models.list():
        if "imagen" in m.name.lower():
            print(m.name)
except Exception as e:
    print(f"Error: {e}")
