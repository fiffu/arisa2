# -*- coding: utf-8 -*-

from cogs.tracking.trackercog import TrackerCog
from .plugmixin import PlugMixin


TOPIC = 'bdplug'

URLS = {
    '★ Notices':
        'https://www.plug.game/browndust/1031684/posts?menuId=1',
    '★ Events (In Progress)':
        'https://www.plug.game/browndust/1031684/posts?menuId=2',
}


class PlugBrownDust(PlugMixin, TrackerCog):
    @property
    def plug_forum_name_urls(self):
        """Mapping[forumName, forumUrl]"""
        return URLS


    @property
    def topic(self):
        return TOPIC
