from collections import Counter
from datetime import datetime
import logging

from discord.ext import commands
from psycopg2.extras import Json

from cogs.mixins import DatabaseCogMixin


log = logging.getLogger(__name__)


ROW_COUNT_HARD_CAP = 5000
ROW_COUNT_SOFT_CAP = 1000



class EmojiStats(DatabaseCogMixin, commands.Cog):
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


    @commands.Cog.listener()
    async def on_reaction_remove(self, reaction, user):
        await self.on_reaction_change(reaction, user, removing=True)


    async def on_reaction_change(self, reaction, user, removing):
        if self.is_me(user):
            return
        emoji_str = str(reaction.emoji)
        userid = user.id
        tstamp = reaction.message.created_at  # in UTC
        await self.bump_emoji_usage(emoji_str, userid, tstamp, removing)


    async def bump_emoji_usage(self,
                               emojistr: str,
                               userid: int,
                               tstamp: datetime,
                               remove: bool):
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


    async def trim_rows(self):
        if self.rows_count < ROW_COUNT_HARD_CAP:
            return

        # Ordered by newest to oldest rows, excluding SOFT_CAP newest rows
        query = f"""
            WITH delete_these AS (
                SELECT * FROM emojistats
                    ORDER BY tstamp DESC
                    OFFSET {ROW_COUNT_SOFT_CAP}
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
        async for row in self.db_query_generating(query):
            ts = row['tstamp']
            # Use latest tstamp in batch as the tstamp for archive row
            if (not tstamp) or (ts > tstamp):
                tstamp = ts
            emoji_ctr[row['emojistr']] += 1

        # Get total count and cast to regular dict before dumping to db
        total_count = sum(emoji_ctr.values())
        emoji_ctr = dict(emoji_ctr)

        query = """
            INSERT INTO emojistats_archive (tstamp, emoji_json, total_count)
            VALUES (%s, %s, %s);"""

        # Push archive row
        await self.db_execute(query,
                              [tstamp, Json(emoji_ctr), total_count])
