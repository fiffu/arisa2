import asyncio
import logging
from typing import Sequence

import aiohttp
from discord.ext import commands, tasks
from selenium import webdriver
from selenium.common.exceptions import WebDriverException

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


import appconfig
from . import config

UPDATE_INTERVAL_SECS = config.TRACKER_UPDATE_INTERVAL_SECS
TIMEOUT_SECS = config.TRACKER_TIMEOUT_SECS

CHROME_BINARY_PATH = appconfig.from_env('GOOGLE_CHROME_BIN')

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

        self.timeout_secs = TIMEOUT_SECS

        interval = self.update_interval_secs
        log.info('[%s] Starting update check loop, interval: %s sec',
                 self._derived_name, interval)
        self._task = tasks.loop(seconds=interval)(self.task)
        self._task.start()


    @property
    def aiohttp_session(self):
        if not hasattr(self, '_aiohttp_session'):
            self._aiohttp_session = aiohttp.ClientSession()
        return self._aiohttp_session


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
        timeout = timeout or self.timeout_secs
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



class SeleniumTrackerCog(TrackerCog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.driver = None


    @property
    def aiohttp_session(self):
        return None


    async def setup_driver(self):
        if self.driver:
            return

        driveroptions = webdriver.chrome.options.Options()
        driveroptions.add_argument('--headless')
        # driveroptions.binary_location = CHROME_BINARY_PATH

        exe_location = CHROME_BINARY_PATH
        if '/app/.apt/' in appconfig.from_env('PATH'):
            # Using options given in by Heroku's Chrome buildpack
            # https://github.com/heroku/heroku-buildpack-google-chrome
            exe_location = 'chromedriver'
            # driveroptions.add_argument('--disable-gpu')
            # driveroptions.add_argument('--no-sandbox')
            # driveroptions.add_argument('--remote-debugging-port=9222')

        log.info('Setting up driver with location: %s', exe_location)
        try:
            self.driver = webdriver.Chrome(executable_path=exe_location,
                                           options=driveroptions)
        except WebDriverException as e:
            log.error('Failed to start driver (%s)', e)
            raise


    async def async_get(self, url, driver=None):
        """Awaitable wrapper over the synchronous driver.get()"""
        driver = driver or self.driver
        return driver.get(url)


    async def fetch(self,
                    url,
                    driver=None,
                    timeout=None,
                    wait=0):
        if not driver:
            if not self.driver:
                await self.setup_driver()
            driver = self.driver

        timeout = timeout or self.timeout_secs

        try:
            task = self.async_get(url, driver)
            await asyncio.wait_for(task, timeout=timeout)
            if wait:
                await asyncio.sleep(wait)
        except asyncio.TimeoutError:
            return None

        return self.driver.page_source


    async def refresh(self, wait=0):
        if not self.driver:
            return

        self.driver.refresh()
        if wait:
            await asyncio.sleep(wait)

        return self.driver.page_source


    async def batch_get_urls(self, *args, **kwargs):
        raise NotImplementedError('Not supported on Selenium drivers')
