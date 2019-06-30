from colorsys import rgb_to_hsv, hsv_to_rgb
from random import random, uniform

from bs4 import BeautifulSoup
import requests


COL_NAME_CACHE = dict()


def fiddle(n, max_dist=0.2, min_dist=0):
    diff = uniform(min_dist, max_dist)
    diff *= -(random() > 0.5) or 1
    return n + diff


def cap(n, floor=0, ceil=1):
    if n < floor:
        return floor
    elif n > ceil:
        return ceil
    else:
        return n


def _mutate(h, s, v, repeats=1):
    global fiddle, cap
    # Bind locally to speedup
    fid = fiddle
    cap = cap
    for _ in range(repeats):
        h = abs(fid(h)) % 1
        s = cap(fid(s))
        v = cap(fid(v))
    return h, s, v


def mutate_hsv(h, s, v, repeats=1):
    return _mutate(h, s, v, repeats)


def mutate_rgb(r, g, b, repeats=1):
    h, s, v = rgb_to_hsv(r, g, b)
    h, s, v = _mutate(h, s, v, repeats)
    return hsv_to_rgb(h, s, v)


def to_hexcode(r, g, b) -> str:
    return ''.join(f'{hex(n)[2:]:>02}' for n in [r, g, b])


def init_name_cache():
    with open('colours.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        COL_NAME_CACHE = {tuple(k.split(',')): v
                          for k, v in data.items()}


def get_colour_name(r, g, b):
    if not COL_NAME_CACHE.get('setup'):
        init_name_cache()
    return COL_NAME_CACHE.get((r, g, b))
