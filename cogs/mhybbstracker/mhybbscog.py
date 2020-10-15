# -*- coding: utf-8 -*-

from cogs.tracking.trackercog import TrackerCog
from .mhybbsmixin import MhyBbsMixin


TOPIC = 'genshin'

# Map[userName, userUrl]
# (actually only the url is used)
URLS = {
    user: f'https://api-takumi.mihoyo.com/post/wapi/userPost?gids=2&size=20&uid={uid}'
    for user, uid in [
        ('原神米游姬', 75276550),
        ('西风快报员', 75276539),
    ]
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
