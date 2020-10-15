"""
TODO: add machine translations for the post titles
"""

from datetime import datetime, timedelta, timezone
import logging
from typing import Sequence

from discord import Embed

from cogs.tracking.config import TRACKER_UPDATE_INTERVAL_SECS


log = logging.getLogger(__name__)

TRACKER_UPDATE_INTERVAL_SECS = 3 * 24 * 60 * 60

class MhyBbsPost:
    URL_STUB = 'https://bbs.mihoyo.com/ys/article/'

    def __init__(self, post_json):
        self.json = post_json


    @property
    def articleid(self):
        return str(self.json['post']['post_id'])  # is a string-encoded int


    @property
    def title(self):
        return self.json['post']['subject']


    @property
    def url(self):
        return self.URL_STUB + self.articleid


    @property
    def image_url(self):
        return self.json['image_list'][0]['url']


    @property
    def author(self):
        user = self.json['user']
        user_url = 'https://bbs.mihoyo.com/ys/accountCenter/postList?id={}'
        return {
            'name': user['nickname'],
            'url': user_url.format(user['uid']),
            'icon_url': user['avatar_url'],
        }


    @property
    def timestamp(self) -> datetime:
        timestamp = int(self.json['post']['created_at'])
        timestamp -= 60 * 60 * 8  # their timestamp is in UTC+8 so drop 8 hours
        return datetime.fromtimestamp(timestamp).astimezone(timezone.utc)


    @property
    def time_since_posted(self) -> timedelta:
        timenow = datetime.now().astimezone(timezone.utc)
        return timenow - self.timestamp


    @property
    def description(self):
        """Not used but could be useful"""
        return self.json['post']['content']


    def to_embed(self, topic):
        try:
            kwargs = {
                attr: getattr(self, attr)
                for attr in (
                    'title',
                    'url',
                    'timestamp',
                    # 'description',
                )
            }

            embed = Embed(**kwargs)

            embed.set_author(**self.author)
            embed.set_image(url=self.image_url)

            embed.set_footer(text='To stop updates from this topic, '
                                  f'type !untrack {topic}')
            return embed

        except Exception as e:
            log.exception(e)
            raise e


    def __repr__(self):
        return f'<MhyBbsPost {self.articleid}: {self.title}>'


class MhyBbsMixin:
    """Mixin to be used with discord.ext.command.Cog"""
    @property
    def update_interval_secs(self) -> int:
        return TRACKER_UPDATE_INTERVAL_SECS


    @property
    def user_name_urls(self):
        """For MihoyoBBS we are tracking posts from user pages

        Map[userName, userUrl]
        """
        raise NotImplementedError


    async def handle_new_posts(self, new_posts: Sequence[MhyBbsPost]) -> None:
        topic = self.topic
        pscog = self.pubsubcog

        if not pscog:
            log.warning('PublishSubscribe not found, unable to publish '
                        '"%s" announces to channels', self.topic)
            return

        channelids = await pscog.get_channelids_by_topic(topic)
        if not channelids:
            log.info('New updates received on topic "%s", but no '
                     'subscribers to be notified.', self.topic)
            return


        posts = sorted(new_posts, key=lambda p: p.timestamp)
        if not posts:
            return

        log.info('%s new posts for topic "%s"', len(posts), topic)

        sendargs = [
            dict(content=None, embed=post.to_embed(self.topic))
            for post in posts
        ]
        await pscog.push_to_topic(self.topic, sendargs)



    async def do_work(self) -> Sequence[MhyBbsPost]:
        #log.info(f'Checking "{self.topic}" for updates...')
        json_responses = await self.pull()

        posts = []

        for json in json_responses:
            post_list = json['data']['list']

            for data in post_list:
                post = MhyBbsPost(data)
                posts.append(post)

        if posts:
            new_posts = self.filtered(posts)
            await self.handle_new_posts(new_posts)

        return True


    def filtered(self,
                 posts: Sequence[MhyBbsPost],
                 cutoff_secs: int = TRACKER_UPDATE_INTERVAL_SECS):
        new_posts = []
        for post in posts:
            time_delta = post.time_since_posted
            time_delta_secs = time_delta.total_seconds()
            if time_delta_secs < cutoff_secs:
                new_posts.append(post)
        return new_posts


    async def pull(self):
        urls = list(self.user_name_urls.values())

        resps = []
        for response in await self.batch_get_urls(self.bot.loop, *urls):
            if response.status == 200:
                resps.append(await response.json())
        return resps
