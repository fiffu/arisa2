import json
import os

from utils.snippets import getabsdir


COL_NAME_CACHE = dict()
COL_NAME_FILE = os.path.join(getabsdir(__file__), 'colours.json')


def to_hexcode(r, g, b) -> str:
    return ''.join(f'{hex(n)[2:]:>02}' for n in [r, g, b])


def init_name_cache():
    with open(COL_NAME_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
        COL_NAME_CACHE = {tuple([int(x) for x in k.split(',')]): v
                          for k, v in data.items()}


def get_colour_name(r, g, b):
    if not COL_NAME_CACHE.get('setup'):
        init_name_cache()
    return COL_NAME_CACHE.get((r, g, b))


def clamp(lowerbound, upperbound):
    def _clamp(val):
        return max(lowerbound, min(val, upperbound))
    return _clamp
