import logging


from discord.ext import commands

log = logging.getLogger('onReadyCog')


class OnReadyCog(commands.Cog):
    """
    Cog that defines bot.on_ready behaviour
    """
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready():
        msg = ('------\n'
               'Logged in.\n'
               '  UN: {}\n'
               '  Invite link:\n'
               '    https://discordapp.com/oauth2/authorize?client_id={}&scope=bot&permissions=0\n'
               '------\n'
        ).format(bot.user.name, bot.user.id)
        log.info(msg)
