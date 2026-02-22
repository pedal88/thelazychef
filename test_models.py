import os
from google import genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
client = genai.Client(api_key=api_key)

try:
    for model in client.models.list():
        print(model.name)
except Exception as e:
    print("Error:", e)
