"""
TODO - make async: either wrap in loop.run_in_executor() or fork and use httpx
"""

from googletrans import Translator


client = Translator()

def translate(text, src='zh-cn', dest='en', replacements=None):
    if replacements:
        for k, v in replacements:
            text = text.replace(k, v)

    result = client.translate(text, src=src, dest=dest)
    return result.text
