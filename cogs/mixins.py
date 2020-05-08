from functools import partial
from inspect import iscoroutinefunction
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
    def __init__(self):
        self._after_setup_pool = []


    @commands.Cog.listener()
    async def on_ready(self):
        await setup_pool()
        if self._after_setup_pool:
            for awaitable in self._after_setup_pool:
                await awaitable()


    def cog_unload(self):
        """cog_unload is an interface specified by discordpy API"""
        close_pool(self.bot.loop)


    def after_setup_pool(self, corofunc):
        """Registers functions to run after database connections are setup"""
        if not iscoroutinefunction(corofunc):
            raise ValueError(f'argument "corofunc" must be a coroutine '
                             f'function (defined with `async def`, or any '
                             f'callable returning an awaitable object), not '
                             f'{type(corofunc)}')
        self._after_setup_pool.append(corofunc)


    async def db_execute(self, *args, **kwargs):
        """Shorthand to plainly execute a statement to the database"""
        rows = []
        pool = await get_pool()
        async with pool.acquire() as conn:
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
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(cursor_factory=DictCursor) as cur:
                await cur.execute(*args, **kwargs)
                try:
                    async for row in cur:
                        rows.append(row)
                except psycopg2.ProgrammingError:
                    # No results
                    pass
        return rows


    async def db_query_generating(self, *args, **kwargs):
        """Similar to db_query(), but yields rows instead of returning list"""
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(cursor_factory=DictCursor) as cur:
                await cur.execute(*args, **kwargs)
                try:
                    async for row in cur:
                        yield row
                except psycopg2.ProgrammingError:
                    # No results
                    pass

# class SomeCog(DatabaseCogMixin, commands.Cog):
#     @commands.Cog.listener()
#     async def on_ready(self):
        # async with self.db_pool.acquire() as conn:
        #     async with conn.cursor() as cur:
        #         resp = await cur.execute("EXPLAIN SELECT * FROM topics")
        #         log.info(repr(resp))

