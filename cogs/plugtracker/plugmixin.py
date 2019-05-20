import datetime
import re
import logging
from typing import Mapping, Sequence

from bs4 import BeautifulSoup
import parsedatetime

from cogs.tracking.config import TRACKER_UPDATE_INTERVAL_SECS


Url = str


calendar = parsedatetime.Calendar()
log = logging.getLogger(__name__)



class PlugPost(object):
    PLUG_STUB = 'https://www.plug.game'
    
    def __init__(self, post_div_soup, forum_name, forum_url):
        self.soup = post_div_soup
        self.forum_name = forum_name
        self.forum_url = forum_url


    @property
    def articleid(self):
        return self.soup['data-articleid']

    
    @property
    def title(self):
        return self.soup.find(class_='tit_feed').text.strip()

    
    @property
    def url(self):
        return self.soup.find(class_='link_rel').attrs['data-url']

    
    @property
    def image_url(self):
        img = self.soup.find(class_='img')
        if not img:
            return None
        
        found = re.search(r'url\((.+)\)$', img['style'])
        return found.groups()[0] if found else None

    
    @property
    def author(self):
        return {
            'name': ' '.join(self.soup.find(class_='name').text.split()),
            'url': self.PLUG_STUB + self.soup.find(class_='name')['href'],
            'icon_url': self.soup.find(class_='thumb')['src'],
        }

    
    @property
    def timestamp(self) -> datetime.datetime:
        def parse_time(time_str):
            # From https://stackoverflow.com/questions/2720319/
            # Find local tz
            now = datetime.datetime.now(datetime.timezone.utc)
            localtz = now.astimezone().tzinfo
            # Parse with parsedatetime NLP
            dt, _ = calendar.parseDT(datetimeString=time_str, tzinfo=localtz)
            # Convert to UTC time, then ISO8601 format
            utc = dt.astimezone(datetime.timezone.utc)
            return utc
        return parse_time(self.soup.find_all(class_='time')[1].text)

    
    @property
    def time_since_posted(self) -> datetime.timedelta:
        timenow = datetime.datetime.now().astimezone(datetime.timezone.utc)
        return timenow - self.timestamp

    
    def __repr__(self):
        return f'<PlugPost {self.articleid}: {self.title}>'


class PlugMixin:
    """Mixin to be used with discord.ext.command.Cog"""    
    @property
    def plug_forum_name_urls(self) -> Mapping[str, Url]:
        """Mapping[forumName, forumUrl]"""
        raise NotImplementedError


    async def handle_new_posts(self, new_posts: Sequence[PlugPost]) -> None:
        pass


    async def do_work(self) -> Sequence[PlugPost]:
        pages = await self.pull_forum_pages()
        
        posts = []

        for page in pages:
            soup = BeautifulSoup(page, 'html.parser')

            forum_name = soup.find('h2', class_='tit_board').text.strip()
            forum_url = self.plug_forum_name_urls.get(forum_name)

            post_divs = soup.find_all(class_='frame_plug')

            # log.info(f'Forum: {forum_name} - {len(post_divs)} posts')

            for div in post_divs:
                post = PlugPost(div, forum_name, forum_url)
                posts.append(post)

        if posts:
            new_posts = self.filtered(posts)
            await self.handle_new_posts(new_posts)
        
        return True


    def filtered(self, 
                 posts: Sequence[PlugPost],
                 cutoff_secs: int = TRACKER_UPDATE_INTERVAL_SECS):
        new_posts = []
        for post in posts:
            time_delta = post.time_since_posted
            time_delta_secs = time_delta.total_seconds()
            if time_delta_secs < cutoff_secs:
                new_posts.append(post)
        return new_posts


    async def pull_forum_pages(self):
        urls = list(self.plug_forum_name_urls.values())
        
        resps = []
        for response in await self.batch_get_urls(self.bot.loop, *urls):
            resps.append(await response.text())
        
        return resps

