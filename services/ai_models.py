"""Every AI model the app calls, and the one shared Gemini client.

Google retires model versions on short notice: in 2026 the Gemini 2.0
models went away and silently broke dish images and chef tips. Change a
model here, never at the call site.
"""
import os

from google import genai

# Text: recipe generation, extraction, evaluation
GEMINI_TEXT = "gemini-flash-latest"
# Text: short, cheap tasks (taxonomy, quick analysis)
GEMINI_TEXT_FAST = "gemini-2.5-flash"

# Images
IMAGEN = "imagen-4.0-generate-001"
IMAGEN_FAST = "imagen-4.0-fast-generate-001"

_client = None


def gemini_client() -> genai.Client:
    """The shared Gemini client. Raises if GOOGLE_API_KEY is missing."""
    global _client
    if _client is None:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable is missing.")
        _client = genai.Client(api_key=api_key)
    return _client
