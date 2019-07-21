import logging
import random
import re
import urllib.parse

from discord.ext import commands
import requests


log = logging.getLogger(__name__)

DEFAULT_ROLL_DICE_COUNT = 1
DEFAULT_ROLL_SIDES = 100
DEFAULT_ROLL_MODIFIER = -1


class General(commands.Cog):
    """
    Misc commands
    """

    def __init__(self, bot):
        self.bot = bot


    @commands.Cog.listener()
    async def on_ready(self):
        log.info(f'Logged in as {self.bot.user.name}.')
        log.info(f'  https://discordapp.com/oauth2/authorize?client_id={self.bot.user.id}&scope=bot&permissions=0\n')


    @commands.command()
    async def roll(self, ctx, *args):
        """Rolls dice (supports algebraic notation, such as !roll 3d5+10)"""
        repatt = r'(?P<dice>\d+(?=d))?[dD]?(?P<sides>\d+)(?P<mod>\s?[-\+]\s?\d+)?'

        dice = DEFAULT_ROLL_DICE_COUNT
        sides = DEFAULT_ROLL_SIDES
        mod = DEFAULT_ROLL_MODIFIER

        match = None
        if args:
            args = ' '.join(args)
            match = re.match(repatt, args)
            if match:
                grps = [x or 0 for x in match.groups()]
                dice, sides, mod = map(int, grps)
                dice = dice or 1  # if `dice` not specified, take as 1

        res = dice * random.randint(1, sides) + mod

        plus = '+' if mod > 0 else ''
        formatted = '{D}d{S}{P}{M}'.format(
            D='' if dice == 1 else dice,
            S=sides,
            P=plus,
            M=mod or ''
        )

        if (dice, sides, mod) == (DEFAULT_ROLL_DICE_COUNT,
                                  DEFAULT_ROLL_SIDES,
                                  DEFAULT_ROLL_MODIFIER):
            formatted = '0-99'

        msg = f"Rolling {formatted}: **{res}**"

        if args and not match:
            msg += '\nTip: `!roll`, `!roll 2`, `!roll d12`, `!roll 3d5+7`'

        await ctx.send(content=msg)


    @commands.command('8ball')
    async def eightball(self, ctx, *args):
        """Concentrate and ask again"""
        ANSWERS = [
            'It is certain.',
            'It is decidedly so.',
            'Without a doubt',
            'Yes - definitely',
            'You may rely on it.',
            'As I see it, yes.',
            'Most likely.',
            'Outlook good.',
            'Yes.',
            'Signs point to yes.',

            'Vision unclear, try again.',
            'Ask again later.',
            'Better not tell you now.',
            'Cannot predict now.',
            'Concentrate and ask again.',

            "Don't count on it.",
            'No.',
            'My sources say no.',
            'Outlook not so good.',
            'Very doubtful.',

            'It is inevitable.',
            'The market demands it.',
            'My calculations say no.',
            "I'm not legally allowed to comment on that.",
        ]

        reply = random.choice(ANSWERS)
        await ctx.send(content=reply)
