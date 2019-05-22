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


class PublishSubscribeCog(DatabaseCogMixin, commands.Cog):
    def __init__(self, bot):
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
        if hasattr(channel, 'name'):
            # TextChannel
            cname = 'Guild::' + channel.name
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
            raise ValueError(f"no such topic registered: '{topic}'")
        
        query = """SELECT channelid, isactive 
                   FROM topics_channels
                   WHERE topic = %s;"""

        rows = await self.db_query(query, [topic])
        
        out = {
            (row['channelid'], row['channelname'])
            for row in rows if row['isactive']
        }
        return out

    
    async def get_topics_by_channel(
            self, channel: ChannelIdentifier) -> Set[str]:

        cid = self._to_channelid(channel)

        query = """SELECT topic 
                   FROM topics_channels 
                   WHERE channelid = %s;"""

        rows = await self.db_query(query, [cid])
        for row in rows:
            log.info(row)
        if not rows:
            return []
        
        return {row['topic'] for row in rows}


    async def push_to_topic(self, 
                            topic: str,
                            sendkwargs) -> Sequence[dict]:
        
        cids = self.get_channelids_by_topic(topic)
        
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
                channel = await self.bot.get_channel(channel)
            
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
            topics = list(self.topics.keys())
        
        ts = set(t for t in topics if t in self.topics)
        non_ts = set(t for t in topics if t not in self.topics)
        
        channel = ctx.message.channel
        cname = self._infer_channel_label(channel)
        cid = channel.id
        await self.subscribe(ts, channel, set_subscribe)

        msgs = []
        if ts:
            s = 's' if len(ts) != 1 else ''
            uns = 'S' if set_subscribe else 'Uns'
            msgs.append(f'{uns}ubscribed to topic{s}: **{", ".join(ts)}**')
            log.info(f'{cname} (id: {cid}) {uns}ubscribed to {", ".join(ts)}')
        if non_ts:
            s = 's' if len(ts) != 1 else ''
            msgs.append(f'Invalid topic{s}: **{", ".join(non_ts)}**')
        if not any([ts, non_ts]):
            msgs.append(self._avail_keys_msg)
        await ctx.send('\n'.join(msgs))

    
    @commands.command()
    async def startann(self, ctx, *topics):
        await self.update_sub(ctx, True, *topics)


    @commands.command()
    async def stopann(self, ctx, *topics):
        await self.update_sub(ctx, True, *topics)


    @commands.command()
    async def listann(self, ctx):
        channel = ctx.message.channel
        subbed = await self.get_topics_by_channel(channel)

        msgs = []
        if subbed:
            msgs.append(f'Subscribed topics for this channel: \n'
                        f'```{", ".join(subbed)}```')
        msgs.append(self._avail_keys_msg)
        await ctx.send('\n'.join(msgs))
