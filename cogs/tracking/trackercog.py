import asyncio
import logging
from typing import Sequence

import aiohttp

from discord.ext import commands, tasks

from . import config


UPDATE_INTERVAL_SECS = config.TRACKER_UPDATE_INTERVAL_SECS
TIMEOUT_SECS = config.TRACKER_TIMEOUT_SECS

log = logging.getLogger(__name__)


class TrackerCog(commands.Cog):
    """Abstract Tracker class that implements the update checking loop

    The do_work() method must be overridden for this cog to operate
    """
    def __init__(self, bot):
        self.bot = bot

        self.update_interval_secs = UPDATE_INTERVAL_SECS
        
        self.aiohttp_timeout_secs = TIMEOUT_SECS
        self.aiohttp_session = aiohttp.ClientSession()

        # self.do_check.change_interval(seconds=UPDATE_INTERVAL_SECS)
        clsname = self._derived_name
        log.info(f'[{clsname}] Starting update check loop, '
                      f'interval: {self.update_interval_secs} sec')
        self._task = tasks.loop(seconds=self.update_interval_secs)(self.task)
        self._task.start()


    @property
    def _derived_name(self):
        return type(self).__name__


    async def do_work(self) -> Sequence:
        clsname = self._derived_name
        log.error(f'{clsname}.do_work() is not implementated.')
        raise NotImplementedError


    def cog_unload(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.aiohttp_session.close())


    async def task(self):
        await self.bot.wait_until_ready()
        proceed = await self.do_work()
        if not proceed:
            log.info('Stopping work on ' + self._derived_name)
            self._task.cancel()
        return


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
