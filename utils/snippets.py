"""snippets.py

Miscellaneous helper functions.
"""

def mash(text: str) -> str:
    """Set input to lowercase and remove non-alphanumeric characters."""
    return ''.join(x for x in text if x.isalnum()).lower()
