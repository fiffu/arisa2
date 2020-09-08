"""snippets.py

Miscellaneous helper functions.
"""

import os.path

def mash(text: str) -> str:
    """Set input to lowercase and remove non-alphanumeric characters."""
    return ''.join(x for x in text if x.isalnum()).lower()

def getabsdir(filepath):
    return os.path.abspath(os.path.dirname(filepath))

def chunkify(it, chunk_size):
    """Yields n-ples from iterable where n is chunk_size"""
    for i in range(0, len(it), chunk_size):
        yield it[i:i+chunk_size]
