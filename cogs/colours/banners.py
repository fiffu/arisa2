"""
banners.py

Defines the colours that go into each banner.
After adding a new banner definition, you have to add it to AVAILABLE_BANNERS
at the bottom of the script so it can be enabled through environment variables

Each banner is a subclass of Pool. The range of colours available in the
banner is represented by HsvPuddle or RgbPuddle objects for the respective
colour space, RGB or HSV.

Each puddle defines a "range" of colours that is described as a statistical
distribution. For example, an RGB "red" puddle would have randomly distributed
R components that are higher than the G or B components.

For every roll on the banner, each component of the resulting colour is
randomized according a statistical distribution that is defined according to
two parameters chosen by you.

For Gaussian distributions, these two parameters are the mean and the SD; for
uniform distributions, they are the upper and lower bounds (inclusive).
"""


import logging
import os

from .pool import Pool, HsvPuddle, RgbPuddle, monochrome_puddle


log = logging.getLogger(__name__)


class HalloweenBanner(Pool):
    """Working Halloween banner with orange, purple and black.
    With extra comments for future reference.
    """

    # Name of banner as displayed to users
    name = 'Halloween!'

    # Banner has 3 colours: orange, purple, black
    puddles = {
        'orange': {
            # Weight is the colour's frequency relative to other colours
            # 40 here means orange is rolled 40 out of (40+55+5) times
            'weight': 40,

            # This puddle uses a HSV colourspace, where
            #   h: normally distributed, mean of 33 degrees, s.d. of 0.05
            #   s: fixed, always 1.0
            #   v: uniformly distributed between [0.8, 0.9]
            # You can use RGB too. Just subclass from RgbPuddle.
            'puddle': HsvPuddle('gaussian', 33/360, 0.05,
                                'uniform', 1.0, 1.0,
                                'uniform', 0.8, 0.9),
        },
        'purple': {
            'weight': 55,
            'puddle': HsvPuddle('gaussian', 324/360, 0.05,
                                'uniform', 0.5, 0.6,
                                'uniform', 0.4, 0.5),
        },
        'black': {
            'weight': 5,
            'puddle': monochrome_puddle(HsvPuddle, 0, 0, 0.01),
        },
    }

    def __init__(self):
        super().__init__()

        for puddleinfo in self.puddles.values():
            pud = puddleinfo.get('puddle')
            weight = puddleinfo.get('weight')

            if pud and weight:
                self.add_puddle(pud, weight)



def get_current_banner():
    AVAILABLE_BANNERS = {
        # key: identifier in environment vars to enable banner
        # value: banner object
        'halloween': HalloweenBanner(),
    }

    selected = os.environ.get('COLOUR_BANNER')
    if not selected:
        return None

    banner = AVAILABLE_BANNERS.get(selected)
    if not banner:
        return None

    not_hsv = lambda x: not isinstance(x, HsvPuddle)
    if any(map(not_hsv, banner.puddles)):
        msg = ('failed to load banner "%s" as only HsvPuddles are supported '
               'at the moment')
        log.error(msg, selected)
        return None

    return banner
