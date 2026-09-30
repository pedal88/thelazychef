import unittest
import sys
import os

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from google.genai import errors
from utils.ai_errors import friendly_ai_error, GENERIC_MESSAGE


def _wrapped_api_error(code, message, status):
    """Mimic ai_engine, which re-raises Gemini errors as ValueError."""
    body = {'error': {'code': code, 'message': message, 'status': status}}
    try:
        try:
            raise errors.ClientError(code, body)
        except Exception as e:
            raise ValueError(f"AI Generation failed: {e}")
    except ValueError as ve:
        return ve


class TestFriendlyAIError(unittest.TestCase):
    def test_billing_depleted(self):
        err = _wrapped_api_error(402, 'Your prepayment credits are depleted.', 'RESOURCE_EXHAUSTED')
        msg = friendly_ai_error(err)
        self.assertIn('billing', msg)
        self.assertNotIn('prepayment', msg)

    def test_rate_limited(self):
        err = _wrapped_api_error(429, 'Quota exceeded', 'RESOURCE_EXHAUSTED')
        self.assertIn('busy', friendly_ai_error(err))

    def test_invalid_key(self):
        err = _wrapped_api_error(400, 'API key not valid.', 'INVALID_ARGUMENT')
        self.assertIn('misconfigured', friendly_ai_error(err))

    def test_non_api_error_uses_fallback(self):
        self.assertEqual(friendly_ai_error(RuntimeError('boom')), GENERIC_MESSAGE)
        self.assertEqual(friendly_ai_error(ValueError('bad'), fallback='custom'), 'custom')


if __name__ == '__main__':
    unittest.main()
