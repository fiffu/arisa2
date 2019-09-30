# -*- coding: utf-8 -*-

from cogs.tracking.trackercog import TrackerCog
from .plugmixin import PlugMixin


TOPIC = 'krplug'

URLS = {
    '[★Notice★]':
        'https://www.plug.game/kingsraid/1030449/posts?menuId=1',
    '[★Patch Note★]':
        'https://www.plug.game/kingsraid/1030449/posts?menuId=9',
    '[★Game Content★]':
        'https://www.plug.game/kingsraid/1030449/posts?menuId=32',
}


class PlugKingsRaid(PlugMixin, TrackerCog):
    @property
    def plug_forum_name_urls(self):
        """Mapping[forumName, forumUrl]"""
        return URLS


    @property
    def topic(self):
        return TOPIC
