"""Calls to Claude for recipe model v2: one streamed request, with usage and cost.

Built in the phase 0b pilot (scripts/pilot_v2b.py). The system prompt (rules,
catalogs, pantry, examples) is the same for every recipe and is cached.
"""
import time

from services.ai_models import CLAUDE_OPUS, CLAUDE_SONNET, claude_client

MAX_TOKENS = 32000
# USD per million tokens: input, output. Cache writes cost 1.25x input, cache reads 0.1x.
PRICES = {CLAUDE_SONNET: (2.0, 10.0), CLAUDE_OPUS: (4.0, 20.0)}


def recipe_json_schema():
    """RecipeV2Schema as a JSON schema for structured output: every object closed, no titles."""
    from pydantic import TypeAdapter

    from schemas.recipe_v2 import RecipeV2Schema

    def clean(node):
        if isinstance(node, dict):
            node.pop('title', None)
            if node.get('type') == 'object':
                node['additionalProperties'] = False
            for v in node.values():
                clean(v)
        elif isinstance(node, list):
            for v in node:
                clean(v)
        return node

    return clean(TypeAdapter(RecipeV2Schema).json_schema())


def usage_of(model, msg, seconds):
    u = msg.usage
    pin, pout = PRICES.get(model, PRICES[CLAUDE_OPUS])
    inp = u.input_tokens or 0
    cw = getattr(u, 'cache_creation_input_tokens', 0) or 0
    cr = getattr(u, 'cache_read_input_tokens', 0) or 0
    out = u.output_tokens or 0
    return {'model': msg.model, 'input_tokens': inp + cw + cr, 'cache_read_tokens': cr, 'output_tokens': out,
            'stop_reason': msg.stop_reason, 'cost_usd': round((inp * pin + cw * pin * 1.25 + cr * pin * 0.1 + out * pout) / 1e6, 6),
            'seconds': round(seconds, 2)}


def call(model, effort, messages, system=None, schema=None):
    """One streamed request. Returns (message, usage). Streaming avoids timeouts on long answers."""
    output_config = {'effort': effort}
    if schema:
        output_config['format'] = {'type': 'json_schema', 'schema': schema}
    kwargs = {'model': model, 'max_tokens': MAX_TOKENS, 'messages': messages, 'output_config': output_config}
    if system:
        kwargs['system'] = [{'type': 'text', 'text': system, 'cache_control': {'type': 'ephemeral'}}]
    t0 = time.time()
    with claude_client().messages.stream(**kwargs) as stream:
        msg = stream.get_final_message()
    return msg, usage_of(model, msg, time.time() - t0)


def text_of(msg):
    return ''.join(b.text for b in msg.content if b.type == 'text')
