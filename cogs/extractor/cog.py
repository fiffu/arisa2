from asyncio import sleep
from collections import defaultdict, namedtuple
from datetime import datetime
from glob import glob
import json
import logging
import os
import re
import sqlite3

from discord.ext import commands
from discord import Emoji, Guild, Object
from discord import DMChannel, GroupChannel, TextChannel
from discord import Forbidden


GUILD_IDS_INFILE = 'guildlist.txt'


# Settings for database and Extractor cache location
here = os.path.dirname(os.path.realpath(__file__))
DATABASE = os.path.join(here, 'extract.db')
DATABASE_SCHEMA = os.path.join(here, 'schema_extractor.sql')
CACHE_DIR = os.path.join(here, 'cache')

# Setup types to make more sense semantically
CustomEmoji = Emoji
ExtractorCached = dict
Snowflake = lambda snowflake_int: Object(id=snowflake_int)
Insertable = namedtuple('Insertable', 'table, columns, values')

CUSTOM_EMOJI_PATTERN = re.compile(r'\<\:(.*?)\:(\d+)\>')

# From mgaitan's comment on GitHub
#   https://gist.github.com/Alex-Just/e86110836f3f93fe7932290526529cd1#gistcomment-3208085
EMOJI_PATTERN = re.compile(
    '['
    '\U0001F1E0-\U0001F1FF'  # flags (iOS)
    '\U0001F300-\U0001F5FF'  # symbols & pictographs
    '\U0001F600-\U0001F64F'  # emoticons
    '\U0001F680-\U0001F6FF'  # transport & map symbols
    '\U0001F700-\U0001F77F'  # alchemical symbols
    '\U0001F780-\U0001F7FF'  # Geometric Shapes Extended
    '\U0001F800-\U0001F8FF'  # Supplemental Arrows-C
    '\U0001F900-\U0001F9FF'  # Supplemental Symbols and Pictographs
    '\U0001FA00-\U0001FA6F'  # Chess Symbols
    '\U0001FA70-\U0001FAFF'  # Symbols and Pictographs Extended-A
    '\U00002702-\U000027B0'  # Dingbats
    '\U000024C2-\U0001F251'
    ']+')


log = logging.getLogger(__name__)


def get_target_guildids(txtfile):
    ids = []

    try:
        with open(txtfile, 'r', encoding='utf-8') as file:
            for i, line in enumerate(file):
                line, *_ = line.split('#', 1)  # Ignore comments
                line = line.strip()

                if not line:
                    continue

                try:
                    ids.append(int(line))

                except ValueError:
                    msg = 'Ignored unexpected "%s" in %s:%s (expected int only)'
                    log.warning(msg, line, file, i+1)

    except FileNotFoundError as exc:
        cls = exc.__class__.__name__
        msg = str(exc)
        log.error('Failed to load guildids from %s (%s: %s)', txtfile, cls, msg)
        ids = []

    return ids


def parse_custom_emoji(emojistr):
    match = CUSTOM_EMOJI_PATTERN.match(emojistr)
    if not match:
        return emojistr, None
    return match.groups()


def find_emoji(str_content):
    if not str_content:
        return
    for name in set(EMOJI_PATTERN.findall(str_content)):
        yield name, None
    for name, customid in set(CUSTOM_EMOJI_PATTERN.findall(str_content)):
        yield name, customid


async def parse_message(message):
    mid = message.id

    channeltype = None
    if isinstance(message.channel, GroupChannel):
        channeltype = 'group'
    elif isinstance(message.channel, DMChannel):
        channeltype = 'dm'

    guildid = message.channel.guild.id if message.channel.guild else None

    insertables = []
    insertables.append(
        InsertFactory.message(messageid=mid,
                              content=message.content,
                              authorid=message.author.id,
                              channelid=message.channel.id,
                              channeltype=channeltype,
                              guildid=guildid))

    insertables.extend(await parse_message_emoji(message.content, message.id))

    for reaction in message.reactions:
        insertables.extend(await parse_reaction(reaction, message.id))

    return insertables


async def parse_message_emoji(content, source_msg_id):
    out = []
    for name, customid in find_emoji(content):
        out.append(
            InsertFactory.emoji(messageid=source_msg_id,
                                emojiname=name,
                                customid=customid))
    return out


async def parse_reaction(reaction, target_msg_id):
    emojistr = str(reaction.emoji)
    name, customid = parse_custom_emoji(emojistr)

    out = []
    async for user in reaction.users():
        out.append(
            InsertFactory.emoji(messageid=target_msg_id,
                                emojiname=name,
                                customid=customid,
                                reacterid=user.id))
    return out


class ExtractCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # Extractors cache; dict of Channelid: ExtractorCached
        # Channelid is the channel's snowflake id
        self.ext_cache = dict()

        self.connection = None


    @commands.Cog.listener()
    async def on_ready(self):
        self.read_cache()

        self.init_db()

        target_guilds = get_target_guildids(txtfile=GUILD_IDS_INFILE)

        found = {g for g in self.bot.guilds
                 if g.id in target_guilds}

        missing = target_guilds - {g.id for g in found}
        if missing:
            log.info('Could not connect to guilds: %s', missing)

        if not found:
            log.info('No guilds to extract from, aborting.')
            return

        num_target = len(target_guilds)
        log.info('Connected to %s of %s target %s: [%s]',
                 len(found),
                 num_target,
                 'guild' if num_target == 1 else 'guilds',
                 ', '.join(f'{g.id}({g.name})' for g in found))

        self.connection = sqlite3.connect(DATABASE)
        try:
            for guild in found:
                await self.extract(guild)
            log.info('Completed extracting from %s guilds', len(found))

            log.info('Updating users...')
            usercount = await self.extract_users()
            log.info('Updated %s users', usercount)

            self.connection.commit()

        except BaseException as exc:
            log.error('Aborting due to exception while extracting (%s: %s)',
                      exc.__class__.__name__,
                      str(exc))

        finally:
            self.connection.close()


    def init_db(self):
        if os.path.exists(DATABASE):
            return

        with open(DATABASE_SCHEMA, 'r', encoding='utf-8') as file:
            schema = file.read()

        with sqlite3.connect(DATABASE) as conn:
            conn.executescript(schema)


    def open_cache(self, path):
        with open(path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            return ExtractorCached(**data)


    def read_cache(self):
        loaded = 0
        for path in glob(os.path.join(CACHE_DIR, '*.json')):
            try:
                cached = self.open_cache(path)
                cid = cached['cid']
                self.ext_cache[cid] = cached
                loaded += 1

            except BaseException as exc:
                log.error('Failed to load %s (%s: %s)',
                          path,
                          exc.__class__.__name__,
                          str(exc))
                continue
        log.info('Loaded %s cached bookmarks from disk', loaded)


    async def extract(self, guild: Guild):
        exts = [self.get_extractor(channel, guild.id)
                for channel in guild.channels
                if isinstance(channel, TextChannel)]

        # Start collecting from the most outdated extractors
        for ext in sorted(exts, key=lambda ext: ext.last_collected):
            try:
                await ext.collect()
            except Forbidden:
                # No read permissions
                log.info('Skipping channel.id=%s (403: No read permissions)',
                         ext.cid)
                continue


    def get_extractor(self,
                      channel: TextChannel,
                      guildid: int = None):

        if not isinstance(channel, TextChannel):
            err = f'{channel} must be TextChannel, not {type(channel)}'
            raise ValueError(err)

        cid = channel.id
        if cid in self.ext_cache:
            cached = self.ext_cache[cid]
            return Extractor.unpickle(cached, self, channel, guildid)
        return Extractor(self, channel, guildid)


    async def extract_users(self):
        """Extract user/display names from collected messages.

        Display names are unique to (userid, guildid).
        """
        cur = self.connection.cursor()

        cur.execute("""SELECT DISTINCT authorid, guildid FROM messages;""")
        # Can use left outer join on `users` to exclude those we've seen before,
        # but UN/DN name may have changed, probably better to re-sync everyone.
        log.info('Selected authors, parsing')

        insert_values = []
        guilds = {}

        for row in cur.fetchall():
            userid, guildid = row[0], row[1]
            guildobj = None

            if guildid in guilds:
                guildobj = guilds[guildid]
            else:
                guildobj = self.bot.get_guild(guildid) if guildid else None
                guilds[guildid] = guildobj

            if guildobj:
                # Fetch guild member
                user = guildobj.get_member(userid)
            else:
                # Fetch regular user
                user = await self.bot.fetch_user(userid)

            username, displayname = None, None
            if user:
                username = str(user)
                displayname = user.display_name or None

            log.info('Fetched uid=%s(UN:%s, DN:%s) from gid:%s',
                     userid, username, displayname, guildid)

            insert_values.append((userid, guildid, username, displayname))

        log.info('Inserting users')
        sql = """INSERT OR IGNORE INTO users
                   (userid, guildid, username, displayname)
                 VALUES (?, ?, ?, ?);"""
        cur.executemany(sql, insert_values)
        cur.execute('COMMIT;')

        return len(insert_values)


    async def push_batch(self, insertables):
        def query(table, cols, tuple_list):
            placeholders = []
            values = []
            for tup in tuple_list:
                # (1, 2, 3, 4) -> '(%s, %s, %s, %s)'
                slots = ','.join('?' for elem in tup)
                placeholders.append(f'({slots})')
                values.extend(tup)

            # join placeholders for each tup
            placeholders = ','.join(placeholders)

            sql = f"""INSERT OR IGNORE INTO {table} {cols}
                      VALUES {placeholders};"""
            return sql, values

        transaction = []

        squashed = defaultdict(list)
        for table, cols, row in insertables:
            squashed[(table, cols)].append(row)

        # Build queries into the transaction
        # Each tuple in `rows` is a set of values forming a row in the db
        # Extend the overall list of values with each tuple
        for (table, cols), rows in squashed.items():
            sql, values = query(table, cols, rows)
            transaction.append((sql, values))

        cur = self.connection.cursor()
        cur.execute('BEGIN TRANSACTION;', ())

        try:
            for sql, values in transaction:
                cur.execute(sql, values or [])
        except BaseException as ex:
            cur.execute('ROLLBACK TRANSACTION;', ())
            return ex

        cur.execute('COMMIT;', ())
        return False


    def update_cache(self, cid, cached):
        self.ext_cache[cid] = cached


class Extractor:
    """Scrapes messages from a TextChannel.

    Scrapes messages from oldest to newest.
    Scraping progress state is cached/reinstated in a file containing the
    timestamp of the most-recently collected message.
    """

    def __init__(self,
                 cog: ExtractCog,
                 channel: TextChannel,
                 guildid: int = None):
        self.cog = cog
        self.channel = channel
        self.cid = channel.id
        self.gid = guildid  # optional

        # Message id (snowflake timestamp)
        self.last_collected: int = 0


    async def collect(self):
        counter = 0

        sleep_interval_msgs = 1000
        start = datetime.utcnow().timestamp()
        time_accum = 0

        log.info('Starting collection on channel.id=%s after=%s',
                 self.cid, self.last_collected)

        after = Snowflake(self.last_collected)
        async for message in self.channel.history(after=after,
                                                  limit=None,
                                                  oldest_first=True):
            insertables = await parse_message(message)

            error = await self.cog.push_batch(insertables)
            if error:
                msg = 'Aborted failed extraction on channel.id=%s (%s: %s)'
                log.error(msg,
                          self.cid,
                          error.__class__.__name__,
                          str(error))
                return
            self.do_cache(message.id)
            counter += 1

            if counter % sleep_interval_msgs == 0:
                now = datetime.utcnow().timestamp()

                elapsed = round(now - start, 2)
                time_accum += elapsed

                start = now

                log.info('channel %s: message #%s (%s) - %s msgs in %s sec',
                         self.cid,
                         counter,
                         message.id,
                         sleep_interval_msgs,
                         elapsed)
                await sleep(0.1)

        log.info('Extracted %s messages from channel.id=%s in %s sec',
                 counter, self.cid, round(time_accum, 2))


    def do_cache(self, timestamp):
        self.update_last_collected(timestamp)
        cached = self.to_cached()
        self.pickle(cached)
        self.cog.update_cache(self.cid, cached)


    def to_cached(self) -> ExtractorCached:
        return ExtractorCached(cid=self.cid,
                               gid=self.gid,
                               timestamp=self.last_collected)


    def pickle(self, cached: ExtractorCached):
        """Not actually a pickle, just dumps object state artifact as json"""
        if not os.path.exists(CACHE_DIR):
            os.mkdir(CACHE_DIR)

        path = os.path.join(CACHE_DIR, f'{self.cid}.json')
        with open(path, 'w', encoding='utf-8') as file:
            json.dump(cached, file)


    @classmethod
    def unpickle(cls,
                 cached: ExtractorCached,
                 cog: ExtractCog,
                 channel: TextChannel,
                 guildid: int = None):
        """Create new instance of extractor and update the timestamp field"""
        new = cls(cog, channel, guildid)
        new.update_last_collected(cached.get('timestamp', 0))
        return new


    def update_last_collected(self, utctime):
        self.last_collected = utctime


    def __hash__(self):
        return self.cid


class InsertFactory:
    """An object holding fields specifying INSERT query params"""
    @classmethod
    def message(cls,
                messageid: int,
                content: str,
                authorid: int,
                channelid: int,
                channeltype: str = None,
                guildid: int = None) -> Insertable:

        return Insertable(
            table='messages',
            columns='(id, content, authorid, channelid, channeltype, guildid)',
            values=(messageid, content, authorid, channelid, channeltype, guildid))


    @classmethod
    def emoji(cls,
              messageid: int,
              emojiname: str,
              count: int = 1,
              customid: int = None,
              reacterid: int = None) -> Insertable:

        return Insertable(
            table='emojiuse',
            columns='(messageid, emojiname, count, customid, reacterid)',
            values=(messageid, emojiname, count, customid, reacterid))
