# -*- coding: utf-8 -*-

from cogs.tracking.trackercog import SeleniumTrackerCog
from .stovemixin import StoveMixin


TOPIC = 'e7stove'

URLS = {
    'General News':
        'https://page.onstove.com/epicseven/global/board/list/e7en001?listType=2&direction=latest&display_opt=usertag_on,html_remove',
    'Game Maintenance':
        'https://page.onstove.com/epicseven/global/board/list/e7en002?listType=2&direction=latest&display_opt=usertag_on,html_remove',
}


class StoveEpicSeven(StoveMixin, SeleniumTrackerCog):
    @property
    def stove_forum_name_urls(self):
        """Mapping[forumName, forumUrl]"""
        return URLS


    @property
    def topic(self):
        return TOPIC
