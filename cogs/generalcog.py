from asyncio import sleep as asleep
import logging
import random
import re

from discord import Embed
from discord.ext import commands


log = logging.getLogger(__name__)

DEFAULT_ROLL_DICE_COUNT = 1
DEFAULT_ROLL_SIDES = 100
DEFAULT_ROLL_MODIFIER = -1

GITHUB_LINK = 'https://github.com/fiffu/arisa2'

BIRB = '<:birb:636038394945863691>'

class General(commands.Cog):
    """
    Misc commands
    """

    def __init__(self, bot):
        self.bot = bot


    @commands.Cog.listener()
    async def on_ready(self):
        log.info('--------------------------------------------------------')
        log.info('Logged in as %s.', self.bot.user.name)
        log.info('  https://discordapp.com/oauth2/authorize?client_id=%s&scope=bot&permissions=0\n',
                 self.bot.user.id)


    @commands.command()
    async def git(self, ctx, *args):
        """Spot a bug? Want to contribute? >> github.com/fiffu/arisa2"""
        emb = Embed(title='GitHub · fiffu/arisa2',
                    description=(f'Bugs and suggestions: create an issue!\n'
                                 f'{GITHUB_LINK}/issues\n\n'
                                 f'Contribtions: pull requests welcome!'
                                 f'```git clone {GITHUB_LINK}.git```'),
                    #url=GITHUB_LINK,
                    colour=0x1e2327)
        await ctx.send(embed=emb)


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
            if len(args) > 30:
                await ctx.send(f"That's just way too much work {BIRB}")
                return

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

        emb = Embed(description=f"Rolling {formatted}: **{res}**")

        if args and not match:
            emb.set_footer('Syntax: !roll, !roll 2, !roll d12, !roll 3d5+7')

        await ctx.send(embed=emb)


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

        async with ctx.typing():
            await asleep(1)
            reply = random.choice(ANSWERS)
            await ctx.send(content=reply)
