from datetime import datetime
import logging
from typing import List

from discord import Embed

import appconfig
from .trackercog import TrackerCog

TOPIC = 'matrix'

USER_LOGINS: List[str] = [
    'mogra',
    #'ztxle',
]

USER_IDS: List[int] = [
    #123
]


# Hardcode avatar urls as lazy workaround for OAuth requirement
AVATAR_URLS = {
    'MOGRA': 'https://static-cdn.jtvnw.net/jtv_user_pictures/mogra-profile_image-f50b50efd00efea3-70x70.jpeg'
}


TWITCH_CLIENT_ID = appconfig.fetch('TWITCH', 'CLIENT_ID')
TWITCH_ENDPOINT_STREAMS = 'https://api.twitch.tv/helix/streams'
TWITCH_ENDPOINT_USERS = 'https://api.twitch.tv/helix/users'

log = logging.getLogger(__name__)
CACHED = dict()


class Stream:
    def __init__(self, **kwargs):
        # Initializing attribs like this will destroy your pylint score
        for k, v in kwargs.items():
            setattr(self, k, v)


    @property
    def update_interval_secs(self):
        """Override so we know within the minute when stream goes up."""
        return 60


    @property
    def cachekey(self):
        name = self.user_name
        time = self.started_at
        _id = self.id  # Frankly not sure if this value is safe to use, lol
        return f'{name}.{time}.{_id}'


    @property
    def timestamp(self):
        return datetime.strptime(self.started_at, '%Y-%m-%dT%H:%M:%SZ')


    def get_thumbnail(self, width, height):
        url = self.thumbnail_url
        url = url.replace('{width}', str(width))
        url = url.replace('{height}', str(height))
        return url


    def to_embed(self, topic):
        emb = Embed(
            title=self.title,
            timestamp=self.timestamp,
            url='https://www.twitch.tv/' + self.user_name,
        )

        if hasattr(self, 'avatar_url') and self.avatar_url:
            emb.set_author(name=self.user_name, icon_url=self.avatar_url)
        else:
            emb.set_author(name=self.user_name)

        emb.set_thumbnail(url=self.get_thumbnail(568, 360))
        emb.set_footer(text=f'To stop receiving updates from this topic, '
                            f'type !untrack {topic}')
        return emb


    def __repr__(self):
        return f'<Stream {self.user_name}: {self.title}>'


class TwitchMogra(TrackerCog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


    @property
    def update_interval_secs(self):
        return 30


    @property
    def topic(self):
        return TOPIC


    def is_matrix_hour(self):
        """Is it past 11pm on the first Saturday of the month?"""
        day, dayofweek, hour = datetime.utcnow().strftime('%d %w %H').split()

        if not (dayofweek == '6'):
            # Fail if not Saturday
            return False

        if not (int(day) <= 7):
            # Fail if not first week of month
            return False

        if not (int(hour) >= 14):
            # Fail if not 11pm or later in Japan Time (UTC+0900)
            # starts at 2300 UTC+9 or 1400 UTC+0
            return False

        return True


    async def get_avatar(self, user_login=None, user_id=None):
        """FIXME: Requires OAuth

        Twitch API docs didn't state the OAuth requirement clearly so I
        wrote all this crap for nothing
        """
        return AVATAR_URLS.get(user_login)
        # if not any([user_login, user_id]):
        #     return None

        # args = []
        # if user_login:
        #     args.append(('user_login', user_login))
        # if user_id:
        #     args.append(('user_id', user_id))

        # resp = await self.fetch(TWITCH_ENDPOINT_USERS,
        #                         headers={'Client-ID': TWITCH_CLIENT_ID},
        #                         params=args)
        # js = await resp.json()
        # log.info(js)
        # data = (js or {}).get('data')
        # if not data:
        #     return None

        # return data[0].get('profile_image_url')


    async def handle_streams(self, apijsondata: List[dict]):
        """Parses API response and feeds to subscribed channels"""
        global CACHED

        pscog = self.pubsubcog
        topic = self.topic

        if not pscog:
            log.warning(f'PublishSubscribe not found, unable to publish '
                        f'"{self.topic}" announces to channels')
            return

        channelids = await pscog.get_channelids_by_topic(topic)
        if not channelids:
            log.info(f'New updates received on topic "{self.topic}", but no '
                     f'subscribers to be notified.')
            return

        live = {}
        for data in apijsondata:
            avatar = await self.get_avatar(user_login=data['user_name'])
            stream = Stream(**data, avatar_url=avatar)
            if stream.cachekey in CACHED:
                continue
            live[stream.cachekey] = stream

        if not live:
            return

        log.info(f'{len(live)} new streams for topic "{topic}"')
        sendargs = [dict(content='Stream is up.',
                         embed=stream.to_embed(topic))
                    for _, stream in live.items()]
        await pscog.push_to_topic(topic, sendargs)

        CACHED = live


    async def pull_streams_by_user(self,
                                   user_logins: List[str],
                                   user_ids: List[int]):
        param_login = [('user_login', x) for x in user_logins]
        param_id = [('user_id', x) for x in user_ids]
        return await self.pull_streams(param_login + param_id)


    async def pull_streams(self, params):
        resp = await self.fetch(TWITCH_ENDPOINT_STREAMS,
                                headers={'Client-ID': TWITCH_CLIENT_ID},
                                params=params)
        js = await resp.json()
        return (js or {}).get('data')


    async def do_work(self):
        if not self.is_matrix_hour():
            return
        streams = await self.pull_streams_by_user(USER_LOGINS, USER_IDS)
        if streams:
            await self.handle_streams(streams)
        return True
