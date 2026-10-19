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

# Images. Imagen 4 was retired from the Gemini API in 2026. The Gemini image
# models take reference images and can edit, which the v2 image flow needs.
# Others available on our key (October 2026): gemini-3.1-flash-image,
# gemini-3.1-flash-lite-image, gemini-3-pro-image. Compare them in the
# prompt lab with --models before switching.
GEMINI_IMAGE = "gemini-2.5-flash-image"

# Claude, for recipe text and structuring in the v2 model (RECIPE_MODEL_V2.md,
# section 7). Which model does which step is decided in phase 0b.
CLAUDE_OPUS = "claude-opus-5-5"
CLAUDE_SONNET = "claude-sonnet-5-5"

_client = None
_claude = None


def gemini_client() -> genai.Client:
    """The shared Gemini client. Raises if GOOGLE_API_KEY is missing."""
    global _client
    if _client is None:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable is missing.")
        _client = genai.Client(api_key=api_key)
    return _client


def claude_client():
    """The shared Anthropic client. Raises if ANTHROPIC_API_KEY is missing."""
    global _claude
    if _claude is None:
        import anthropic

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is missing.")
        _claude = anthropic.Anthropic(api_key=api_key, max_retries=4)
    return _claude
