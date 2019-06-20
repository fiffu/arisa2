from colorsys import rgb_to_hsv, hsv_to_rgb
from random import random, uniform


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
