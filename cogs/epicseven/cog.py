from functools import partial
import logging

from discord import Embed
from discord.ext import commands

from .model import BadConstraintError, calculator

log = logging.getLogger(__name__)


SYMBOLS_EMOJI = {
    'knight': '<:knight:632504202395910146>',
    'mage': '<:mage:632504308671184907>',
    'ranger': '<:ranger:632504248340316160> ',
    'soul weaver': '<:soulweaver:632504221836640266>',
    'thief': '<:thief:632504280657690634>',
    'warrior': '<:warrior:632504180300578816>',
    'defbreak': '<:defbreak:632507984974577675>',
}


def digest(phrase, dot='. '):
    *initials, last = phrase.split()
    initials = [x[0] for x in initials]
    if not initials:
        return phrase
    return f"{''.join(initials)}{dot or ''}{last}"


def conjunctify(iterable,
                fmtbody='{},',
                joinwith=' ',
                oxford=False,
                prefinal='and'):
    *body, lastword = list(iterable)

    words = [fmtbody.format(e) for e in body]
    if not oxford:
        words[-1] = body[-1]

    if prefinal:
        words.append(prefinal)

    words.append(lastword)

    return joinwith.join(words)


def interpret_whitelist(whitelist, digestnames=True):
    if not whitelist:
        return 'Any hero'

    names = whitelist.get('Name', [])
    if names:
        return digest(names[0]) if digestnames else names[0]

    classes = [SYMBOLS_EMOJI[c] for c in whitelist.get('Class', [])]
    class_str = ''.join(classes) or 'hero'
    defbreak = whitelist.get('HasDefenseDown', [])
    defbreak = f' with {SYMBOLS_EMOJI["defbreak"]}' if defbreak else ''
    return f'Any {class_str}{defbreak}'


class EpicSeven(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    async def async_calculate(self, *args, **kwargs):
        calc = partial(calculator, *args, **kwargs)
        loop = self.bot.loop
        result = await loop.run_in_executor(None, calc)
        return result


    async def find_optimum_morale(self, ctx, choices, whitelists):
        # chat1 = self.format_choice(*first, wid_l_hero, wid_l_chat)
        # chat2 = self.format_choice(*second, wid_r_hero, wid_r_chat)

        msg_len_cap = 1024 * 30
        msglen = 0

        conditions = [interpret_whitelist(w) for w in whitelists]
        header = 'Highest morale yield matching conditions: '
        header += f'**{" / ".join(conditions)}**\n'
        msglen += len(header)

        lines = []
        for (team, first, second) in choices:
            teamstr = ', '.join(digest(name.title(), dot=' ') for name in team)
            total = first[0] + second[0]
            line = f'**+{total:<2}**: {teamstr}\n'
            msglen += len(line)
            if msglen > msg_len_cap:
                break
            lines.append(line)

        embed = Embed(description=''.join([header, *lines]))
        await ctx.send(embed=embed)


    @commands.command(
        help='Lab morale calculator. Write hero names separated by a '
             'comma.\nShortforms are supported, so "bell" will be treated '
             'as Bellona, and "sbell" as Seaside Bellona.\n\nYou can give '
             'constraints instead of heroes using "?". For example, ?mage '
             'will search for any Mage heroes, and ?war?def will search '
             'for warriors with defense break. Use a single ? to indicate '
             'ANY hero, without constraints.\n\nSupported constraints:\n'
             '  ?<class> (?mage, ?thief etc)\n  ?defbreak\n\n'
             'Example:  !camp ravi, fceci, ?mage, ?war?def')
    async def camp(self, ctx, *heronames, maxteams=10):
        """Lab morale calculator."""
        max_unconstrained = 3  # More than 3 will take forever
        heronames = [h.strip()
                     for h in ' '.join(heronames).lower().split(',')]

        unconstrained = heronames.count('?')
        if unconstrained > max_unconstrained:
            await ctx.send("You can only choose up to {max_unconstrained} "
                           "unconstrained heroes! You'll get an answer much "
                           "faster if you provide constraints, such as `?w` "
                           "to allow only warriors in that slot in the team.")
            return

        if unconstrained > 2:
            await ctx.send('Hang on -- this will literally take a minute...')

        try:
            choices, whitelists = await self.async_calculate(*heronames,
                                                             maxteams=maxteams)
        except BadConstraintError as e:
            await ctx.send(f'No such constraint: "?{e.val}"')
            return

        if not choices:
            await ctx.send("Hmm, looks like something's wrong with your "
                           "query! Check if you have duplicated hero and "
                           "try again!")
            return

        if len(choices) != 1:
            await self.find_optimum_morale(ctx, choices, whitelists)
            return

        team, first, second = choices[0]
        total = first[0] + second[0]
        lines = [f'**{total:>2}** morale:']
        for chat in [first, second]:
            gain, name, topic = chat
            topic = ' '.join(topic.split('-')).title()
            lines.append(f'{gain:>2} from {name.title()} - {topic}')
        body = '\n'.join(lines)

        team = [f'**{t.title()}**' for t in team]
        header = f'Camping with {conjunctify(team, oxford=False)}\n'

        embed = Embed(description=header + body)
        await ctx.send(embed=embed)
        return
