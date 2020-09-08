from asyncio import sleep as asleep
from datetime import datetime
import logging
import random
import re

from discord import Embed
from discord.ext import commands

from utils import chunkify

log = logging.getLogger(__name__)

DEFAULT_ROLL_DICE_COUNT = 1
DEFAULT_ROLL_SIDES = 100
DEFAULT_ROLL_MODIFIER = -1

GITHUB_LINK = 'https://github.com/fiffu/arisa2'

BIRB = '<:birb:715571534726430761>'

HOT_TIME = None
HOT_TIME_DURATION_SECS = 30
HOT_TIME_TRIGGER_CHANCE = 0.10
HOT_TIME_BONUS = 1.0

def is_hot_time():
    global HOT_TIME
    if HOT_TIME:
        elapsed = (datetime.now() - HOT_TIME).total_seconds()
        return elapsed < HOT_TIME_DURATION_SECS
    if random.random() < HOT_TIME_TRIGGER_CHANCE:
        HOT_TIME = datetime.now()
        log.info('HOT TIME NOW!!1')
        return True
    return False


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
                                 f'Contributions: pull requests welcome!'
                                 f'```git clone {GITHUB_LINK}.git```'),
                    #url=GITHUB_LINK,
                    colour=0x1e2327)
        await ctx.send(embed=emb)


    @commands.command()
    async def roll(self, ctx, *args):
        """Rolls dice (supports algebraic notation, such as !roll 3d5+10)"""
        def parseint(x):
            try:
                return int(x or 0)
            except ValueError:
                return x

        repatt = (                      # !roll 3d5+10 check these dubs
            r'(?P<dice>\d+(?=d))?'      #       3
            r'[dD]?'                    #        d
            r'(?P<sides>\d+)'           #         5
            r'(?P<mod>\s?[-\+]\s?\d+)?' #          +10
            r'(?P<comment>.*)'          #              check these dubs
        )

        dice = DEFAULT_ROLL_DICE_COUNT
        sides = DEFAULT_ROLL_SIDES
        mod = DEFAULT_ROLL_MODIFIER
        footer = ''

        match = None
        if args:
            args = ' '.join(args).strip()
            match = re.match(repatt, args)

            if not match:
                # If there was args but no match, offer a tip
                footer = 'Syntax: !roll 1000, !roll 3d5+7, !roll 11d9 check em'

            else:
                # Unpack message into arithmetic inputs
                *nums, comment = match.groups()
                footer = comment.strip() or ''
                dice, sides, mod = map(parseint, nums)

                # Check if it's too much work
                if len(''.join(nums)) > 20:
                    await ctx.send(f"That's just way too much work {BIRB}")
                    return

        # Calc output
        res = dice * random.randint(1, sides) + mod

        # Format output
        if is_hot_time():
            # suppose res == 12345; transform to '||12||||34||||5||'
            bigrammed = lambda s: chunkify(s, 2)
            res = ''.join(
                f'||{pair}||'
                for pair in bigrammed(str(res))
            )

        # Format input into algebraic notation or 0-99
        formatted = '{D}d{S}{P}{M}'.format(
            D='' if dice == 1 else dice,
            S=sides or 0,
            P=('+' if mod > 0 else '-') if mod else '',
            M=mod or ''
        )

        if (dice, sides, mod) == (DEFAULT_ROLL_DICE_COUNT,
                                  DEFAULT_ROLL_SIDES,
                                  DEFAULT_ROLL_MODIFIER):
            formatted = '0-99'

        # Build embed and set comment or tip
        emb = Embed(description=f"Rolling {formatted}: **{res}**")
        if footer:
            emb.set_footer(text=footer)

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
