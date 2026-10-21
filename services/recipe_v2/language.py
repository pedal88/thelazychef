"""The language a recipe is written in (recipe.language, ISO 639-1).

A recipe is one recipe in every language: the graph, amounts, times and metadata are shared, and only
the human-readable text (title, component and line names, steps, the chef's note) is written in a
language. recipe.language is the language of that text as it was made; other languages come later as
translations of the text layer. English is the default.
"""
LANGUAGES = {'en': 'English', 'nb': 'Norwegian (bokmål)'}  # code -> what the prompt says
DEFAULT = 'en'


def code_of(value):
    """A language code from a form or a task: the code itself, or the prompt name that older tasks carried."""
    if value in LANGUAGES:
        return value
    return next((code for code, name in LANGUAGES.items() if name == value), None)


def prompt_name(code):
    """What the prompt calls the language, or None to write in the language of the idea or the source."""
    return LANGUAGES.get(code)
