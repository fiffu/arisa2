from collections import Counter, OrderedDict
from datetime import datetime
from itertools import chain
import logging
import re

from discord import Embed
from discord.ext import commands
from psycopg2.extras import Json

from appconfig import DEBUGGING
from cogs.mixins import DatabaseCogMixin


log = logging.getLogger(__name__)


ROW_COUNT_HARD_CAP = 5000
ROW_COUNT_SOFT_CAP = 1000

EMOJI_STRING_PATTERN = re.compile(r'\<\:(?P<name>.+)\:(?P<uid>\d+)\>')


def find_emoji(str_content):
    for name, uid in set(EMOJI_STRING_PATTERN.findall(str_content)):
        raw = f'<:{name}:{uid}>'
        yield raw, name, uid


def embed_from_emoji_tups(emoji_tup_list):
    if len(emoji_tup_list) > 10:
        emoji_tup_list = emoji_tup_list[:10]

    embed = Embed()

    for raw, name, uid in emoji_tup_list:
        url = f'https://cdn.discordapp.com/emojis/{uid}.png'
        fieldname = f'`:{name}:`'
        fieldvalue = f'{raw} [link]({url})'
        embed.add_field(name=fieldname, value=fieldvalue, inline=True)

    if not emoji_tup_list:
        embed.description = "_(Couldn't detect any custom emoji)_"
    else:
        uid = emoji_tup_list[0][1]
        url = f'https://cdn.discordapp.com/emojis/{uid}.png'
        embed.set_image(url=url)

    return embed


def cleave_emoji(emoji_str):
    matched = EMOJI_STRING_PATTERN.match(emoji_str)
    if not matched:
        return (None, None)
    name, uid = matched.groups()
    return name, uid


class EmojiTools(DatabaseCogMixin, commands.Cog):
    """
    Stats for emoji nerds
    """

    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self.rows_count = 0
        self.after_setup_pool(self.get_row_count)


    async def get_row_count(self):
        rows = await self.db_query("SELECT * FROM emojistats;")
        self.rows_count = len(rows)


    def is_me(self, user):
        return self.bot.user.id == user.id


    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        await self.on_reaction_change(reaction, user, removing=False)


    # @commands.Cog.listener()
    # async def on_reaction_remove(self, reaction, user):
    #     await self.on_reaction_change(reaction, user, removing=True)


    async def on_reaction_change(self, reaction, user, removing):
        if self.is_me(user):
            return

        emoji = reaction.emoji

        emoji_str = str(emoji)
        userid = user.id
        tstamp = reaction.message.created_at  # in UTC
        await self.bump_emoji_usage(emoji_str, userid, tstamp, removing)


    @commands.Cog.listener()
    async def on_message(self, message):
        if self.is_me(message.author):
            return

        if message.content.startswith(self.bot.command_prefix):
            return

        userid = message.author.id
        tstamp = message.created_at

        for raw, _, _ in find_emoji(message.content):
            await self.bump_emoji_usage(raw,
                                        userid,
                                        tstamp,
                                        remove=False)


    async def bump_emoji_usage(self,
                               emojistr: str,
                               userid: int,
                               tstamp: datetime,
                               remove: bool):
        if DEBUGGING:
            log.info('Skip %scrementing for %s',
                     'de' if remove else 'in',
                     emojistr)
            return

        query = """
            INSERT INTO emojistats(emojistr, userid, tstamp)
                VALUES (%s, %s, %s)
                ON CONFLICT (emojistr, userid, tstamp)
                    DO NOTHING;"""

        if remove:
            query = """
                DELETE FROM emojistats
                    WHERE emojistr = %s
                    AND userid = %s
                    AND tstamp = %s;"""

        await self.db_execute(query, [emojistr, userid, tstamp])
        self.rows_count += (-1 if remove else 1)

        if remove:
            return
        await self.trim_rows()


    async def trim_rows(self, force=False):
        if (not force) and (self.rows_count < ROW_COUNT_HARD_CAP):
            return

        if self.rows_count == 0:
            log.info('No rows to trim')
            return

        # Ordered by newest to oldest rows, excluding SOFT_CAP newest rows
        query = f"""
            WITH delete_these AS (
                SELECT * FROM emojistats
                    ORDER BY tstamp DESC
                    OFFSET {0 if force else ROW_COUNT_SOFT_CAP}
            )
            DELETE FROM emojistats
                WHERE (tstamp, userid, emojistr)
                IN (SELECT * FROM delete_these)
            RETURNING *;"""

        # Timestamp to use on the archive row
        tstamp = None

        # For counting emoji among rows targeted for archiving
        emoji_ctr = Counter()

        # Push row data into counter object
        for row in await self.db_query(query):
            ts = row['tstamp']
            # Use latest tstamp in batch as the tstamp for archive row
            if (not tstamp) or (ts > tstamp):
                tstamp = ts
            emoji_ctr[row['emojistr']] += 1

        # Get total count
        total_count = sum(emoji_ctr.values())

        query = """
            INSERT INTO emojistats_archive (tstamp, emoji_json, total_count)
            VALUES (%s, %s, %s);"""

        # Push archive row
        await self.db_execute(query,
                              [tstamp, Json(emoji_ctr), total_count])
        log.info('Trimmed emojistats into archive, tstamp=%s',
                 tstamp.timestamp())


    @commands.command()
    async def picfor(self, ctx, *args):
        """Provides the link to the picture of a given (custom) emoji"""
        args = ' '.join(args)
        embed = embed_from_emoji_tups(find_emoji(args))
        await ctx.send(embed=embed)


    @commands.command()
    async def steal(self, ctx):
        """Steals emoji from recent messages in the channel you use this in"""
        messages = await ctx.history(limit=10).flatten()

        local_emojis = []
        if ctx.guild:
            local_emojis = list(filter(lambda e: cleave_emoji(str(e))[1],
                                       ctx.guild.emojis))

        # Use ordered dict so most recently-encountered emoji will appear
        # at the top of the embed result
        emoji_found_tups = OrderedDict()
        for message in messages:
            # Stop if we've reached the embed fields threshold of 10 fields
            if len(emoji_found_tups) >= 10:
                break

            # Combine message and reacts into single string for easy searching
            text = message.content + (
                ' '.join(str(r) for r in message.reactions))

            for raw, name, uid in find_emoji(text):
                key = (raw, name, uid)
                if (uid not in local_emojis) and (key not in emoji_found_tups):
                    emoji_found_tups[key] = None

        emoji_found_tups = list(emoji_found_tups.keys())[:10]

        embed = embed_from_emoji_tups(emoji_found_tups)
        await ctx.send(embed=embed)


    @commands.command(hidden=True)
    async def trim(self, ctx):
        if not await self.bot.is_owner(ctx.author):
            return
        await self.trim_rows(force=True)


    @commands.command(hidden=True)
    async def scrape(self, ctx, guild_id=None, channel_id=None):
        if not await self.bot.is_owner(ctx.author):
            return

        if guild_id:
            guild = self.bot.get_guild(int(guild_id))
        else:
            guild = ctx.guild

        if not guild:
            log.info('scrape: could not find guild id: %s', guild_id)
            return

        log.info('scrape: starting on guild id: %s', guild.id)

        if channel_id:
            # guild.get_channel() returns List[discord.abc.GuildChannel] or None
            channel = guild.get_channel(channel_id)
            channels = [channel]

        else:
            channels = guild.channels

        if not any(channels):
            log.info('scrape: could not find any channels, aborting '
                     '(guild_id: %s channel_id: %s)',
                     guild_id,
                     channel_id)
            return

        channels_scraped = 0
        rows_added = 0
        parse = self.parse_msg_for_emoji

        for channel in filter(None, channels):
            # Voice channels have no history
            if not hasattr(channel, 'history'):
                continue

            try:
                async for uids_reacts in channel.history().map(parse):
                    unique_reacts = len(uids_reacts)
                    if not unique_reacts:
                        continue

                    # psycopg2 placeholders that are substituted for actual data
                    # during execute
                    placeholders = ','.join(['(%s, %s, %s)'] * unique_reacts)
                    query = (f'INSERT INTO emojistats(tstamp, userid, emojistr) '
                             f'VALUES {placeholders} ON CONFLICT DO NOTHING;')

                    # Flatten the data
                    # [(uid, raw)...] -> [time, uid1, raw1, time, uid2, raw2...]
                    data = list(chain.from_iterable(uids_reacts))

                    await self.db_execute(query, data)
                    rows_added += unique_reacts

                    if rows_added >= ROW_COUNT_HARD_CAP:
                        log.info('scrape: exceeded hardcap, halting (%s >= %s)',
                                 rows_added, ROW_COUNT_HARD_CAP)
                        break
                channels_scraped += 1

            except BaseException as e:
                log.info('scrape: failed to scrape channel id: %s (%s: %s)',
                         channel.id, e.__class__.__name__, e)

        log.info('scrape: scraped %s unique reacts from %s channels',
                 rows_added, channels_scraped)
        await self.trim_rows()


    async def parse_msg_for_emoji(self, message):
        author_id = message.author.id
        tstamp = message.created_at
        # This function parses emoji as having same timestamp as the message it
        # reacts to (as opposed to when the react was added). This is to
        # consistently count instances of emoji use as unique to each message
        # (using the timestamp as a unique identifier).

        content_emoji = set((author_id, raw)
                            for raw, _, _ in find_emoji(message.content))

        content_emoji_add = content_emoji.add

        for react in message.reactions:
            react_raw = str(react)
            async for user in react.users():
                content_emoji_add((user.id, react_raw))

        return [(tstamp, user_id, react_raw)
                for user_id, react_raw in content_emoji]
