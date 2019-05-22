# -*- coding: utf-8 -*-

import logging
from typing import Mapping, Sequence

from cogs.tracking.trackercog import TrackerCog
from .plugmixin import PlugMixin, PlugPost


log = logging.getLogger(__name__)


TOPIC = 'bdplug'

URLS = {
    '★ Notices':
        'https://www.plug.game/browndust/1031684/posts?menuId=1',
    '★ Events (In Progress)':
        'https://www.plug.game/browndust/1031684/posts?menuId=2',
}


class PlugBrownDustCog(PlugMixin, TrackerCog):
    def __init__(self, bot):
        self.bot = bot


    @property
    def plug_forum_name_urls(self) -> Mapping[str, str]:
        """Mapping[forumName, forumUrl]"""
        return URLS


    @property
    def topic(self):
        return TOPIC
