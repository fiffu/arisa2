import logging
import os

from .pool import Pool, HsvPuddle, static_puddle


log = logging.getLogger(__name__)


BANNERS = None

class HalloweenBanner(Pool):
    orange_weight = 40
    orange = HsvPuddle('gaussian', 33/360, 0.05,
                       'uniform', 1.0, 1.0,
                       'uniform', 0.8, 0.9)

    purple_weight = 55
    brown = HsvPuddle('gaussian', 324/360, 0.05,
                      'uniform', 0.5, 0.7,
                      'uniform', 0.4, 0.5)

    black_weight = 5  # SSR
    black = static_puddle(HsvPuddle, 0, 0, 0.01)

    def __init__(self):
        super().__init__()

        for colour in ['orange', 'brown', 'black']:
            pud = getattr(self, colour)
            weight = getattr(self, colour + '_weight')

            self.add_puddle(pud, weight)



def get_current_banner():
    global BANNERS

    if not BANNERS:
        BANNERS = {
            'halloween': HalloweenBanner(),
        }

    selected = os.environ.get('COLOUR_BANNER')
    if not selected:
        return None

    banner = BANNERS.get(selected)
    if not banner:
        return None

    not_hsv = lambda x: not isinstance(x, HsvPuddle)
    if any(map(not_hsv, banner.puddles)):
        msg = ('failed to load banner "%s" as only HsvPuddles are supported '
               'at the moment')
        log.error(msg, selected)
        return None

    return banner
