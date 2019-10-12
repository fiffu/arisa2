import datetime
import re
import logging
from typing import Mapping, Sequence

from bs4 import BeautifulSoup
from discord import Embed

from cogs.tracking.config import TRACKER_UPDATE_INTERVAL_SECS

Url = str

log = logging.getLogger(__name__)


# Driver takes 30+ secs to get one page, so make the interval at least 60 secs
# This should change when bulk fetch is implementated on SeleniumTrackerCog
TRACKER_UPDATE_INTERVAL_SECS = max(60, TRACKER_UPDATE_INTERVAL_SECS)


class StovePost(object):
    def __init__(self, soup, forum_name, forum_url):
        self.soup = soup
        self.forum_name = forum_name
        self.forum_url = forum_url


    @property
    def articleid(self):
        x = self.url.rsplit('/', 1) or [None]
        return x[-1]


    @property
    def title(self):
        if hasattr(self, '_title'):
            return self._title
        div = self.soup.find('div', class_='table__td__subject__wrapper--text')
        self._title = div.text.strip()
        return self._title


    @property
    def url(self):
        if hasattr(self, '_url'):
            return self._url
        subject = self.soup.find('div', class_='table__td__subject')
        self._url = subject.find('a').attrs['href']
        return self._url


    @property
    def image_url(self):
        """FIXME: Find a threadsafe way to grab the post's banner

        So far, we have to put in a http call to the event page to pull out
        the banner. Using the driver takes too long and the driver's state is
        not threadsafe.
        One possible solution is to modify fetch() to spin up a driver (or
        fork from the existing one) every time we need to grab a page, but
        we need ot check the memory overhead of doing that first.
        """
        if hasattr(self, '_image_url'):
            return self._image_url

        if '[Event]' in self.title:
            self._image_url = 'https://i.imgur.com/NmOjFEb.png'
        else:
            self._image_url = 'https://i.imgur.com/iqv0kEr.png'

        return self._image_url


    @property
    def author(self):
        user = self.soup.find('td', class_='table__td td-user').find('a')

        url = user.attrs.get('href')

        # Monkey patch to fix weird Stove url
        if url.startswith('//www'):
            url = 'https:' + url

        return {
            'name': user.text.strip(),
            'url': url,
            'icon_url': user.find('img').attrs.get('src'),
        }


    @property
    def timestamp(self) -> datetime.datetime:
        if hasattr(self, '_timestamp'):
            return self._timestamp

        dateelem = self.soup.find('td', class_='table__td td-date')
        datestr = dateelem.find('time').attrs.get('datetime')

        dt = datetime.datetime.strptime(datestr, '%Y-%m-%dT%H:%M')
        # dt = dt.astimezone(datetime.timezone.utc)

        dt = dt.replace(tzinfo=datetime.timezone.utc)

        self._timestamp = dt
        return self._timestamp


    @property
    def time_since_posted(self) -> datetime.timedelta:
        timenow = datetime.datetime.now().astimezone(datetime.timezone.utc)
        return timenow - self.timestamp


    def to_embed(self, topic):
        try:
            kwargs = {
                attr: getattr(self, attr)
                for attr in ('title', 'url', 'timestamp')
            }

            embed = Embed(**kwargs)

            embed.set_author(**self.author)
            embed.set_image(url=self.image_url)

            fname, furl = self.forum_name, self.forum_url
            forumlink = f'[{fname}]({furl})'
            embed.add_field(name='Posted in forum', value=forumlink)
            embed.set_footer(text='To stop receiving updates from this topic, '
                                  f'type !untrack {topic}')
            return embed

        except Exception as e:
            log.exception(e)
            raise e


    def __repr__(self):
        return f'<StovePost {self.articleid}: {self.title}>'


class StoveMixin:
    """Mixin to be used with discord.ext.command.Cog"""
    @property
    def stove_forum_name_urls(self) -> Mapping[str, Url]:
        """Mapping[forumName, forumUrl]"""
        raise NotImplementedError


    async def handle_new_posts(self, new_posts: Sequence[StovePost]) -> None:
        topic = self.topic
        pscog = self.pubsubcog

        if not pscog:
            log.warning(f'PublishSubscribe not found, unable to publish '
                        f'"{self.topic}" announces to channels')
            return

        channelids = await pscog.get_channelids_by_topic(topic)
        if not channelids:
            log.info(f'New updates received on topic "{self.topic}", but no '
                     f'subscribers to be notified.')
            return

        posts = sorted(new_posts, key=lambda p: p.timestamp)
        if not posts:
            return

        s = 's' if len(posts) != 1 else ''
        log.info(f'{len(posts)} new posts for topic "{topic}"')

        sendargs = [
            dict(content=None, embed=post.to_embed(self.topic))
            for post in posts
        ]
        await pscog.push_to_topic(self.topic, sendargs)


    async def do_work(self) -> Sequence[StovePost]:
        #log.info(f'Checking "{self.topic}" for updates...')
        pages = await self.pull_forum_pages()

        posts = []

        for page in pages:
            try:
                soup = BeautifulSoup(page, 'html.parser')

                forum_name = soup.find('h3', class_='page--content__title').text
                forum_url = self.stove_forum_name_urls.get(forum_name)

                container = soup.find('div', class_='page--board')
                elems = container.find_all('tr', class_='checkbox')

                # log.info(f'Forum: {forum_name} - {len(post_divs)} posts')

                for elem in elems:
                    post = StovePost(elem, forum_name, forum_url)
                    posts.append(post)
            except BaseException as e:
                url = ''
                try:
                    url = f' at {forum_url}'
                except NameError:
                    pass
                cls = e.__class__.__name__
                log.error('Failed to parse page{url} ({cls}: {e})')

        if posts:
            new_posts = self.filtered(posts)
            await self.handle_new_posts(new_posts)

        return True


    def filtered(self,
                 posts: Sequence[StovePost],
                 cutoff_secs: int = TRACKER_UPDATE_INTERVAL_SECS):
        new_posts = []
        seen_id = set()

        for post in posts:
            if post.articleid in seen_id:
                continue
            seen_id.add(post.articleid)

            time_delta = post.time_since_posted
            time_delta_secs = time_delta.total_seconds()
            if time_delta_secs < cutoff_secs:
                new_posts.append(post)
        return new_posts


    async def pull_forum_pages(self):
        urls = list(self.stove_forum_name_urls.values())

        resps = []
        start = datetime.datetime.now()

        for url in urls:
            src = await self.fetch(url, wait=10)
            resps.append(src)

        elapsed_secs = (datetime.datetime.now() - start).total_seconds()
        log.info('Pulled %s pages (t=%ss)', len(urls), elapsed_secs)
        return resps
