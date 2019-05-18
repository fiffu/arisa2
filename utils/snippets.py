def mash(text):
    return ''.join(x for x in text if x.isalnum()).lower()
