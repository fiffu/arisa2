import logging
import sys

import discord
from discord.ext import commands

from appconfig import DEBUGGING


log = logging.getLogger(__name__)

class DebugCog(commands.Cog):
    """
    Cog that defines bot.on_ready behaviour
    """

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        if DEBUGGING:
            log.critical(f'DebugCog loaded -- app will terminate on error')

    @commands.Cog.listener()
    async def on_error(self, event, *args, **kwargs):
        if not DEBUGGING:
            return
        exctype, excobj, traceb = sys.exc_info()
        if not any([exctype, excobj, traceb]):
            return
        log.critical(f'Halting due to {exctype}: {str(excobj)} '
                     f')via event "{event}")')
        log.exception(excobj)
        await self.bot.close()
