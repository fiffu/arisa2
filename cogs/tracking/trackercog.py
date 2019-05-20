import asyncio
import logging
from typing import Sequence

import aiohttp

from discord.ext import commands, tasks

from . import config


UPDATE_INTERVAL_SECS = config.TRACKER_UPDATE_INTERVAL_SECS
TIMEOUT_SECS = config.TRACKER_TIMEOUT_SECS


class TrackerCog(commands.Cog):
    """Abstract Tracker class that implements the update checking loop

    The do_work() method must be overridden for this cog to operate
    """
    def __init__(self, bot):
        self.bot = bot
        self.log = logging.getLogger(__name__)

        self.update_interval_secs = UPDATE_INTERVAL_SECS
        
        self.aiohttp_timeout_secs = TIMEOUT_SECS
        self.aiohttp_session = aiohttp.ClientSession()
        self.results = None

        # self.do_check.change_interval(seconds=UPDATE_INTERVAL_SECS)
        self.task.start()


    @property
    def _derived_name(self):
        return type(self).__name__


    async def do_work(self) -> Sequence:
        clsname = self._derived_name
        self.log.error(f'{clsname}.do_work() is not implementated.')
        raise NotImplementedError


    @tasks.loop(seconds=UPDATE_INTERVAL_SECS)
    async def task(self):
        stop = await self.do_work()
        if stop:
            self.task.cancel()
        return


    @task.before_loop
    async def before_do_work(self):
        await self.bot.wait_until_ready()
        clsname = self._derived_name
        self.log.info(f'[{clsname}] Starting update check loop, '
                      f'interval: {self.update_interval_secs} sec')


    async def fetch(self, url, session=None, timeout=None):
        session = session or self.aiohttp_session
        timeout = timeout or self.aiohttp_timeout_secs
        return await session.get(url, timeout=timeout)


    async def batch_get_urls(self,
                             loop,
                             *urls,
                             session=None,
                             return_exceptions=False):
        session = session or self.aiohttp_session

        responses = await asyncio.gather(
            *[self.fetch(url, session=session) for url in urls],
            loop=loop,
            return_exceptions=return_exceptions
        )

        return responses
