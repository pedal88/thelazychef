from google.genai import errors as genai_errors

GENERIC_MESSAGE = "Something went wrong generating the recipe. Please try again."


def _find_api_error(exc):
    """Walk the exception chain (ai_engine re-raises Gemini errors as ValueError)."""
    seen = set()
    while exc is not None and id(exc) not in seen:
        if isinstance(exc, genai_errors.APIError):
            return exc
        seen.add(id(exc))
        exc = exc.__cause__ or exc.__context__
    return None


def friendly_ai_error(exc, fallback=GENERIC_MESSAGE):
    """Map an exception to a message that is safe to show users.

    The raw error should still be logged by the caller.
    """
    api_error = _find_api_error(exc)
    if api_error is None:
        return fallback

    code = getattr(api_error, 'code', None)
    status = getattr(api_error, 'status', None) or ''
    if code == 402 or (code == 429 and 'credit' in str(api_error).lower()):
        return "AI generation is temporarily unavailable (billing). Please contact the admin."
    if code == 429 or status == 'RESOURCE_EXHAUSTED':
        return "The AI is busy right now. Please try again in a minute."
    if code in (400, 401, 403) and ('API key' in str(api_error) or status in ('PERMISSION_DENIED', 'UNAUTHENTICATED')):
        return "The AI service is misconfigured. Please contact the admin."
    if code in (500, 502, 503, 504):
        return "The AI service is having problems right now. Please try again shortly."
    return fallback
