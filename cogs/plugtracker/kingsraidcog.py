# -*- coding: utf-8 -*-

import logging
from typing import Mapping, Sequence

from cogs.tracking.trackercog import TrackerCog
from .plugmixin import PlugMixin, PlugPost


log = logging.getLogger(__name__)


TOPIC = 'krplug'

URLS = {
    '[★Notice★]':
        'https://www.plug.game/kingsraid/1030449/posts?menuId=1',
    '[★Patch Note★]':
        'https://www.plug.game/kingsraid/1030449/posts?menuId=9',
    '[★Game Content★]':
        'https://www.plug.game/kingsraid/1030449/posts?menuId=32',
}


class PlugKingsRaidCog(PlugMixin, TrackerCog):
    @property
    def plug_forum_name_urls(self) -> Mapping[str, str]:
        """Mapping[forumName, forumUrl]"""
        return URLS


    @property
    def topic(self):
        return TOPIC
