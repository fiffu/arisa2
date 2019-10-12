import logging
import traceback

import discord
from discord.ext import commands

import appconfig

DEBUGGING = appconfig.DEBUGGING

log = logging.getLogger(__name__)


class DebugCog(commands.Cog):
    """
    Cog that defines bot.on_ready behaviour
    """

    def __init__(self, bot):
        self.bot = bot
        self.halting = DEBUGGING or False


    @commands.Cog.listener()
    async def on_ready(self):
        if self.halting:
            log.critical(f'App will halt on command invoke error')

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        try:
            raise error

        finally:
            cls = error.__class__.__name__
            msg = str(error)

            log.error('%s: %s | cog: %s, author: %s, text: %s',
                      cls, msg, ctx.cog, str(ctx.author), ctx.message.content)

            tb = traceback.format_exc()
            log.error(f'%s: %s', cls, tb)

            if DEBUGGING:
                msg = f'{cls}: {msg}```\n{tb}```'
                await ctx.send(content=msg)

        # finally:
            if not DEBUGGING:
                return
            if not self.halting:
                await ctx.send(content='App skipped halting.')
                return
            await ctx.send(content='App halting.')
            log.critical(f'Halting due to command error...')
            await self.bot.close()


    async def sethalt(self, boolean):
        if not DEBUGGING:
            return
        val = boolean and DEBUGGING
        log.info(f'Set halting to {val} (DEBUGGING: {DEBUGGING})')
        self.halting = val


    @commands.command(hidden=True)
    async def nohalt(self, ctx):
        await self.sethalt(False)


    @commands.command(hidden=True)
    async def halt(self, ctx):
        await self.sethalt(True)


    @commands.command(hidden=True)
    async def echo(self, ctx):
        m = ctx.message
        await ctx.send(m)
        await ctx.send(m.content)
        await ctx.send(f'```{m.content}```')


    @commands.command(hidden=True)
    async def die(self, ctx):
        if not (DEBUGGING or await self.bot.is_owner(ctx.author)):
            return
        await ctx.send('Bot closing.')
        await self.bot.close()
