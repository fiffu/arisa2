import logging

import discord
from discord.ext import commands


class OnReadyCog(commands.Cog):
    """
    Cog that defines bot.on_ready behaviour
    """
    logger = logging.getLogger(__name__)
    
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.logger.info(f'Logged in as {self.bot.user.name}.')
        self.logger.info(f'  https://discordapp.com/oauth2/authorize?client_id={self.bot.user.id}&scope=bot&permissions=0\n')
