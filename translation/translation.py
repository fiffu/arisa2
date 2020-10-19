"""
TODO - make async: either wrap in loop.run_in_executor() or fork and use httpx
"""

from googletrans import Translator


rd = {
    '原神': 'Genshin',
    '可莉': 'Klee',
}

client = Translator()

def translate(text, src='zh-cn', dest='en', replacements=None):
    if replacements:
        for k, v in replacements.items():
            text = text.replace(k, v)

    result = client.translate(text, src=src, dest=dest)
    return result.text


def main():
    s = """
    《原神》角色演示

    「可莉：哒哒哒」
    """
    print(translate(s, replacements=rd))

if __name__ == '__main__':
    main()
