# -*- coding: utf-8 -*-

from cogs.tracking.trackercog import TrackerCog
from .sgxmixin import SgxMixin


TOPIC = 'sgxresearch'


class SgxResearch(SgxMixin, TrackerCog):
    @property
    def topic(self):
        return TOPIC
