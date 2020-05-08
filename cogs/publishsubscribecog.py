from collections import defaultdict
import logging
from typing import List, Sequence, Set, Union

from discord import TextChannel, DMChannel, GroupChannel, DiscordException
from discord.ext import commands
import psycopg2

from .mixins import DatabaseCogMixin


# Type aliases
Channel = Union[TextChannel, DMChannel, GroupChannel]
ChannelId = int
ChannelIdentifier = Union[Channel, ChannelId]


log = logging.getLogger(__name__)


class NotChannelError(ValueError):
    pass


class PublishSubscribe(DatabaseCogMixin, commands.Cog):
    """The interface between channel subscribes and updates from TrackerCogs"""

    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self.topics = defaultdict(list)


    @property
    def _avail_keys_msg(self):
        topics = sorted(list(self.topics.keys()))
        topics.append('all')
        return (f'Available topics: \n'
                f'```{", ".join(topics)}```')


    def _to_channelid(self, channel: ChannelIdentifier):
        cid = channel.id if hasattr(channel, 'id') else channel

        if not isinstance(cid, ChannelId):
            raise NotChannelError(
                f"'{repr(channel)}' is not a valid channel or channel ID")

        return cid


    def _infer_channel_label(self, channel: Channel):
        cname: str
        if hasattr(channel, 'name') and hasattr(channel, 'guild'):
            # TextChannel
            cname = 'Guild-' + channel.guild.name + '::' + channel.name
        elif hasattr(channel, 'recipient'):
            # DMChannel
            cname = 'DM::' + str(channel.recipient)
        elif hasattr(channel, 'recipients'):
            # GroupChannel
            cname = 'Group::' + str(channel)
        else:
            raise ValueError("'channel' arg has no name")

        return cname


    def register_cog_to_topic(self,
                              topic: str,
                              cog: commands.Cog):
        self.topics[topic].append(cog)
        cogname = cog.qualified_name
        log.info(f'Registered {cogname} under topic "{topic}"')


    async def get_channelids_by_topic(self, topic: str) -> Set[ChannelId]:
        if topic not in self.topics:
            exc = ValueError(f"no such topic registered: '{topic}'")
            log.exception(exc)
            raise exc

        query = """SELECT channelid, isactive
                   FROM topics_channels
                   WHERE topic = %s AND isactive = %s;"""

        rows = await self.db_query(query, [topic, True])

        out = {
            (row.get('channelid'), row.get('channelname'))
            for row in rows
        }
        return out


    async def get_topics_by_channel(
            self, channel: ChannelIdentifier) -> Set[str]:

        cid = self._to_channelid(channel)

        query = """SELECT topic
                   FROM topics_channels
                   WHERE channelid = %s AND isactive = %s;"""

        rows = await self.db_query(query, [cid, True])
        if not rows:
            return []

        return {row.get('topic') for row in rows}


    async def push_to_topic(self,
                            topic: str,
                            sendkwargs) -> Sequence[dict]:

        cids = await self.get_channelids_by_topic(topic)

        for cid, cname in cids:
            channel = self.bot.get_channel(cid)
            if not channel:
                log.warning(f'invalid channel: {cname} id: {cid}')
                continue

            for kwargs in sendkwargs:
                try:
                    await channel.send(**kwargs)
                except DiscordException as e:
                    args = ', '.join([f'{k}={v}' for k, v in kwargs.items()])
                    msg = f'failed send({args}) to channel: {cname} id: {cid}'
                    log.exception(msg)


    async def subscribe(self,
                        topics: Sequence[str],
                        channel: ChannelIdentifier,
                        set_isactive: bool = True):
        try:
            if type(channel) is ChannelId:
                channel = self.bot.get_channel(channel)

            if not channel:
                raise NotChannelError("'channel' arg was invalid")

            topics = set(topics)

            cid: ChannelId = channel.id
            cname: str = self._infer_channel_label(channel)

            guildid: int = None
            guildname: str = None
            if hasattr(channel, 'guild'):
                guildid = channel.guild.id
                guildname = channel.guild.name

            isactive: bool = set_isactive

            query = """DELETE FROM topics_channels
                       WHERE (channelid=%s AND topic=%s);
                       INSERT INTO
                           topics_channels(
                               topic,
                               channelid, channelname,
                               guildid, guildname,
                               isactive
                           )
                       VALUES (%s, %s, %s, %s, %s, %s);"""

            for topic in topics:
                await self.db_execute(
                    query, [
                        cid, topic,
                        topic, cid, cname, guildid, guildname, isactive
                    ]
                )

        except (NotChannelError, psycopg2.OperationalError) as e:
            log.exception('failed to subscribe/unsubscribe due to error')


    async def update_sub(self, ctx, set_subscribe=True, *topics):
        if 'all' in topics:
            topics = sorted(list(self.topics.keys()))

        topics = [''.join([c for c in topic if c.isalnum()])
                  for topic in topics]

        # Valid topic args
        ts = set(t for t in topics if t in self.topics)
        # Invalid topic args
        non_ts = set(t for t in topics if t not in self.topics)

        channel = ctx.message.channel
        cname = self._infer_channel_label(channel)
        cid = channel.id
        await self.subscribe(ts, channel, set_subscribe)

        msgs = []
        if ts:
            s = 's' if len(ts) != 1 else ''
            uns = 'S' if set_subscribe else 'Uns'
            to = 'to' if set_subscribe else 'from'
            msgs.append(f'{uns}ubscribed {to} topic{s}: **{", ".join(ts)}**')
            log.info(f'{cname} (id: {cid}) {uns}ubbed {to} {", ".join(ts)}')
        if non_ts:
            s = 's' if len(ts) != 1 else ''
            msgs.append(f'Invalid topic{s}: **{", ".join(non_ts)}**')
        if not any([ts, non_ts]):
            msgs.append(self._avail_keys_msg)
        await ctx.send('\n'.join(msgs))


    @commands.command()
    async def track(self, ctx, *topics):
        """Starts updates for a topic in this channel (to list topics: !track)
        """
        await self.update_sub(ctx, True, *topics)


    @commands.command()
    async def untrack(self, ctx, *topics):
        """Stops updates for a topic in this channel (stop all: !untrack all)
        """
        await self.update_sub(ctx, False, *topics)


    @commands.command()
    async def tracking(self, ctx):
        """Shows the topics that this channel receives updates for"""
        channel = ctx.message.channel
        subbed = await self.get_topics_by_channel(channel)

        msgs = []
        if subbed:
            msgs.append(f'Subscribed topics for this channel: \n'
                        f'```{", ".join(subbed)}```')
        msgs.append(self._avail_keys_msg)
        await ctx.send('\n'.join(msgs))
