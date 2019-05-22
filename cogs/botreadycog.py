import logging

import discord
from discord.ext import commands


log = logging.getLogger(__name__)

class BotReadyCog(commands.Cog):
    """
    Cog that defines bot.on_ready behaviour
    """
    
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        log.info(f'Logged in as {self.bot.user.name}.')
        log.info(f'  https://discordapp.com/oauth2/authorize?client_id={self.bot.user.id}&scope=bot&permissions=0\n')
