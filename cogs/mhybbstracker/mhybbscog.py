# -*- coding: utf-8 -*-

from cogs.tracking.trackercog import TrackerCog
from .mhybbsmixin import MhyBbsMixin


TOPIC = 'genshin'

# Map[userName, userUrl]
# (actually only the url is used)
URLS = {
    '西风快报员': 'https://api-takumi.mihoyo.com/post/wapi/userPost?gids=2&size=20&uid=75276539',
    '原神米游姬': 'https://api-takumi.mihoyo.com/post/wapi/userPost?gids=2&size=20&uid=75276550',
    'en_events': 'https://api-os-takumi.mihoyo.com/community/post/wapi/getNewsList?gids=2&page_size=20&type=2',
    'en_info': 'https://api-os-takumi.mihoyo.com/community/post/wapi/getNewsList?gids=2&page_size=10&type=3',
}


class MhyBbs(MhyBbsMixin, TrackerCog):
    @property
    def user_name_urls(self):
        """For MihoyoBBS we are tracking posts from user pages

        Returns Mapping[userName, userUrl]
        """
        return URLS


    @property
    def topic(self):
        return TOPIC
