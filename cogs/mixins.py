import logging

from discord.ext import commands
import psycopg2
from psycopg2.extras import DictCursor

from database import setup_pool, get_pool, close_pool


log = logging.getLogger(__name__)


class DatabaseCogMixin:
    """Singleton-like Cog mixin for acquiring connections to the app database.
    
    This mixin is designed to work with subclasses of discord.ext.commands.Cog
    only. Its basic purpose is to provide bindings to modules that interface
    the app database, as well as to automatically setup and teardown the
    connection pool when the cog is loaded/unloaded.
    """
    @property
    def db_pool(self):
        return get_pool()


    @commands.Cog.listener()
    async def on_ready(self):
        await setup_pool()


    def cog_unload(self):
        close_pool()


    async def db_execute(self, *args, **kwargs):
        """Shorthand to plainly execute a statement to the database"""
        rows = []
        async with self.db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(*args, **kwargs)
                try:
                    async for row in cur:
                        rows.append(row)
                except psycopg2.ProgrammingError:
                    # No results
                    pass
        return rows

    
    async def db_query(self, *args, **kwargs):
        """Similar to db_execute(), but uses a DictCursor for reading"""
        rows = []
        async with self.db_pool.acquire() as conn:
            async with conn.cursor(cursor_factory=DictCursor) as cur:
                await cur.execute(*args, **kwargs)
                try:
                    async for row in cur:
                        rows.append(row)
                except psycopg2.ProgrammingError:
                    # No results
                    pass
        return rows

# class SomeCog(DatabaseCogMixin, commands.Cog):
#     @commands.Cog.listener()
#     async def on_ready(self):
        # async with self.db_pool.acquire() as conn:
        #     async with conn.cursor() as cur:
        #         resp = await cur.execute("EXPLAIN SELECT * FROM topics")
        #         log.info(repr(resp))

