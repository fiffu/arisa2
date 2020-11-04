# -*- coding: utf-8 -*-

from discord.ext import commands

from cogs.tracking.trackercog import TrackerCog
from .mixin import YahooFinanceMixin


class Stonks(YahooFinanceMixin, TrackerCog):
    @property
    def symbols(self):
        """For MihoyoBBS we are tracking posts from user pages

        Returns Mapping[userName, userUrl]
        """
        return {
            'S58.SI': 'SATS Ltd.',
            'G3B.SI': 'Nikko AM ETF',
            'VL6.SI': 'Koufu Group Limited',
        }

    @property
    def topic(self):
        return 'stonks'
