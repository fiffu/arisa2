from collections import Counter
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

EMOJI_STRING_PATTERN = re.compile(r'\<\:(?P<name>.*?)\:(?P<uid>\d+)\>')


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
        embed.add_field(name=raw, value=f'[`:{name}:`]({url})', inline=True)

    if len(emoji_tup_list) == 1:
        uid = emoji_tup_list[0][1]
        url = f'https://cdn.discordapp.com/emojis/{uid}.png?v=1'
        # FIXME: set_image and set_thumbnail both don't seem to work. 
        # Maybe Discord hates people embedding their resources?
        embed.set_thumbnail(url=url)

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

        emoji_str = str(reaction.emoji)

        userid = user.id

        tstamp = reaction.message.created_at  # in UTC
        recipientid = reaction.message.author.id

        await self.bump_emoji_usage(emoji_str, userid, tstamp, recipientid,
                                    removing)


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
                               recipientid: int = None,
                               remove: bool = False):
        if DEBUGGING:
            log.info('Skip %scrementing for %s',
                     'de' if remove else 'in',
                     emojistr)
            return

        query = """
            INSERT INTO emojistats(emojistr, userid, tstamp, recipientid)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT DO NOTHING;"""
        data = [emojistr, userid, tstamp, recipientid]

        if remove:
            query = """
                DELETE FROM emojistats
                    WHERE emojistr = %s
                    AND userid = %s
                    AND tstamp = %s;"""
            data = [emojistr, userid, tstamp]

        await self.db_execute(query, data)
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

        # Ordered by newest to oldest rows, offsetting SOFT_CAP newest rows
        query = f"""
            WITH delete_these AS (
                SELECT * FROM emojistats
                    ORDER BY tstamp DESC
                    --LIMIT NULL OFFSET {0 if force else ROW_COUNT_SOFT_CAP}
                    LIMIT NULL OFFSET 1000
            )
            DELETE FROM emojistats
                USING delete_these
                WHERE emojistats.tstamp = delete_these.tstamp
                AND emojistats.userid = delete_these.userid
                AND emojistats.emojistr = delete_these.emojistr
                AND emojistats.recipientid = delete_these.recipientid
            RETURNING *;"""

        # Timestamp to use on the archive row
        tstamp = None

        # For counting emoji among rows targeted for archiving
        emoji_ctr = Counter()

        # Push archived rows into counter object
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
        """Gets you the source pic of the given (custom) emoji"""
        emoji = list(find_emoji(' '.join(args)))
        if not emoji:
            await ctx.send(f"You have to specify a custom emoji that you have "
                           f"access to. (Hint: if you don't have access, you "
                           f"can `{self.bot.command_prefix}steal` it!)")
            return

        embed = embed_from_emoji_tups(emoji)

        await ctx.send(embed=embed)


    @commands.command()
    async def steal(self, ctx):
        """Steals emoji from recent messages in the channel you use this in"""
        messages = await ctx.history(limit=10).flatten()

        # Use ordered dict so most recently-encountered emoji will appear
        # at the top of the embed result
        emoji_found_tups = []
        for message in messages:
            # Stop if we've reached the embed fields threshold of 10 fields
            if len(emoji_found_tups) >= 10:
                break

            # Combine message and reacts into single string for easy regexing
            reacts = ' '.join(str(r) for r in message.reactions)
            text = message.content + reacts

            for raw, name, uid in find_emoji(text):
                key = (raw, name, uid)
                if key not in emoji_found_tups:
                    emoji_found_tups.append(key)

        emoji_found_tups = emoji_found_tups[:10]

        embed = embed_from_emoji_tups(emoji_found_tups)
        embed.set_footer(text="Not what you're looking for? This command only "
                              "shows the 10 latest custom emoji used in this "
                              "channel!")

        await ctx.send(embed=embed)


    @commands.command(hidden=True)
    async def trim(self, ctx):
        """Immediately flush emojistats to archive regardless of table length"""
        if not await self.bot.is_owner(ctx.author):
            return
        await self.trim_rows(force=True)


    @commands.command(hidden=True)
    async def scrape(self, ctx, guild_id=None, channel_id=None):
        """Scrapes all emoji usage from the target guild or channel.

        WARNING: Currently the db doesn't index the origin guild, so this
        command will conflate emoji usage stats from the target guild with the
        guild that this command was issued from.
        """
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
        emojis_scraped = 0
        parser = self.parse_msg_emoji

        # filter() out any Nones return by guild.get_channel()
        for channel in filter(None, channels):
            # Voice channels have no history
            if not hasattr(channel, 'history'):
                continue

            try:
                async for uids_reacts in channel.history().map(parser):
                    emojis_scraped += await self.ingest_emoji(uids_reacts)

                channels_scraped += 1

            except AssertionError:
                break

            except BaseException as e:
                if DEBUGGING:
                    raise
                log.info('scrape: failed to scrape channel id: %s (%s: %s)',
                         channel.id, e.__class__.__name__, e)

        log.info('scrape: scraped %s unique reacts from %s channels',
                 emojis_scraped, channels_scraped)
        await self.trim_rows()


    async def parse_msg_emoji(self, message):
        """Parses a message for emoji in the content and the reacts.

        This function parses emoji as having same timestamp as the message it
        reacts to (as opposed to when the react was added). This is to
        consistently count instances of emoji use as unique to each message
        (using the timestamp as a unique identifier).
        """
        author_id = message.author.id
        tstamp = message.created_at

        content_emoji = set((author_id, raw, None)
                            for raw, _, _ in find_emoji(message.content))

        content_emoji_add = content_emoji.add

        for react in message.reactions:
            react_raw = str(react)
            async for user in react.users():
                content_emoji_add((user.id, react_raw, author_id))

        return [(tstamp, *tup) for tup in content_emoji]


    async def ingest_emoji(self, uids_reacts):
        """Inserts emoji usage instances to database.

        uids_reacts should be an iterable yielding 'usage instances', each
        'instance' being a 4-ple of (tstamp, userid, emojistr, recipientid)
        corresponding to a row in the emojistats table in the database.
        """
        unique_reacts = len(uids_reacts)
        if not unique_reacts:
            return 0

        current_rows_count = self.rows_count
        if current_rows_count + unique_reacts > ROW_COUNT_HARD_CAP:
            log.info('scrape: exceeding hardcap, stop ingesting (%s + %s)',
                     current_rows_count, unique_reacts)
            raise AssertionError

        # psycopg2 placeholders that are substituted for actual data
        # during execute
        placeholders = ','.join(['(%s, %s, %s, %s)'] * unique_reacts)
        query = (f'INSERT INTO emojistats(tstamp, userid, emojistr, recipientid) '
                 f'VALUES {placeholders} ON CONFLICT DO NOTHING;')

        # Flatten the data
        # [(uid, raw)...] -> [time, uid1, raw1, time, uid2, raw2...]
        data = list(chain.from_iterable(uids_reacts))

        await self.db_execute(query, data)
        self.rows_count += unique_reacts
        return unique_reacts
