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

    The do_work() method and topic() property must be overridden for this cog
    to work. You can make do_work() return False to stop it from being
    repeated.

    You may override update_interval_secs() to change the interval at which
    do_work() is repeated.

    For detailed explanation, see the README.
    """
    def __init__(self, bot):
        self.bot = bot

        self.aiohttp_timeout_secs = TIMEOUT_SECS
        self.aiohttp_session = aiohttp.ClientSession()

        interval = self.update_interval_secs
        log.info('[%s] Starting update check loop, interval: %s sec',
                 self._derived_name, interval)
        self._task = tasks.loop(seconds=interval)(self.task)
        self._task.start()


    @property
    def topic(self) -> str:
        """Used with pubsubcog for users to subscribe to updates from this cog
        """
        return None


    @property
    def update_interval_secs(self) -> int:
        """Override to change time interval between each do_work() call

        Fractions should work as well but I haven't tested that. It's probably
        a bad idea to repeat stuff more than once a second anyway.
        """
        return UPDATE_INTERVAL_SECS


    async def do_work(self) -> bool:
        """This method will be periodically invoked until it returns False

        This method must be overridden by subclasses.
        """
        clsname = self._derived_name
        msg = f'{clsname}.do_work() is not implementated.'
        log.error(msg)
        raise NotImplementedError(msg)


    @property
    def pubsubcog(self):
        """Convenient access to the pubsubcog"""
        pscog = self.bot.get_cog('PublishSubscribe')
        if not pscog:
            mycls = self.__class__.__name__
            log.warning('PublishSubscribe not found, please ensure that '
                        f'it is loaded before {mycls} in cogs.__init__')
        return pscog


    @commands.Cog.listener()
    async def on_ready(self):
        if not self.topic:
            return
        if self.pubsubcog:
            self.pubsubcog.register_cog_to_topic(self.topic, self)
        else:
            log.warning(f'PublishSubscribe not found, failed to register '
                        f'topic "{self.topic}"')


    def cog_unload(self):
        # Frankly no idea if this works, never used it before
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.aiohttp_session.close())


    async def task(self):
        """Coro to serve as argument to discord.ext.tasks.loop()"""
        await self.bot.wait_until_ready()
        proceed = await self.do_work()
        if proceed is False:
            log.info('Stopping work on ' + self._derived_name)
            self._task.cancel()
        return


    async def fetch(self,
                    url,
                    session=None,
                    headers=None,
                    params=None,
                    timeout=None):
        """GETs a page, returning an aiohttp.ClientResponse object

        Note that aiohttp does not handle `params` the same way as requests.
        requests will accept lists as args to params, but aiohttp only
        allows strings as args.
        As a workaround, to pass a list to a param, write:
            param=[('key', val1), ('key', val2), ('key', val3)]
        """
        session = session or self.aiohttp_session
        timeout = timeout or self.aiohttp_timeout_secs
        return await session.get(url,
                                 headers=headers,
                                 params=params,
                                 timeout=timeout)


    async def batch_get_urls(self,
                             loop,
                             *urls,
                             session=None,
                             headers=None,
                             params=None,
                             return_exceptions=False):
        """Conveniently abstracts over fetch() to grab multiple pages"""
        session = session or self.aiohttp_session

        responses = await asyncio.gather(
            *[
                self.fetch(url,
                           headers=headers,
                           params=params,
                           session=session)
                for url in urls
            ],
            loop=loop,
            return_exceptions=return_exceptions
        )

        return responses


    @property
    def _derived_name(self):
        """The name of the subclass derived from this cog"""
        return type(self).__name__
