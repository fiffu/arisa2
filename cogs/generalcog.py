import logging
import re

import discord
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

    @commands.command()
    async def roll(self, ctx, *args):
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

        res = dice * randint(1, sides) + mod

        plus = '+' if mod > 0 else ''
        formatted = '{D}d{S}{P}{M}'.format(
            D='' if dice == 1 else dice,
            S=sides,
            P=plus,
            M=mod or ''
        )

        if (dice, sides, mod) == ROLL_DEFAULT:
            formatted = '0-99'

        msg = f"Rolling {formatted}: **{res}**"

        if args and not match:
            msg += '\nTip: `!roll`, `!roll 2`, `!roll d12`, `!roll 3d5+7`'

        await ctx.send(content=msg)


    @commands.command('8ball')
    async def eightball(self, ctx, *args):
        question = ' '.join(args)
        qn = urllib.parse.quote(question)
        r = requests.get("https://8ball.delegator.com/magic/JSON/" + qn)
        reply = "Response unclear, consider turning it off and on again."
        if r.ok:
            reply = r.json()['magic']['answer']
        await ctx.send(content=reply)
