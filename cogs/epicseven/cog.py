import logging

from discord import Embed
from discord.ext import commands

from .model import calculator

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


    async def find_optimum_morale(self, ctx, choices, whitelists):
        # chat1 = self.format_choice(*first, wid_l_hero, wid_l_chat)
        # chat2 = self.format_choice(*second, wid_r_hero, wid_r_chat)

        msg_len_cap = 1024 * 30
        msglen = 0

        conditions = [interpret_whitelist(w) for w in whitelists]
        header = '> Highest morale yield matching conditions: '
        header += f'**{" / ".join(conditions)}**\n'
        msglen += len(header)

        lines = []
        for (team, first, second) in choices:
            teamstr = ', '.join(digest(name.title(), dot='.') for name in team)
            total = first[0] + second[0]
            line = f'> +{total:<2}: {teamstr}\n'
            msglen += len(line)
            if msglen > msg_len_cap:
                break
            lines.append(line)

        msg = ''.join([header, *lines])
        await ctx.send(msg)


    @commands.command(
        help='Lab morale calculator. Write hero names separated by a
             'comma `,`. Shortforms are supported, so `bell` will be treated '
             'as `Bellona`, and `sbell` as `Seaside Bellona`. You can provide '
             'constraints instead of heroes using `?`. For example, `?mage` '
             'will search for any Mage heroes, and `?war?def` will search for '
             'warriors with defense break.')
    async def camp(self, ctx, *heronames, maxteams=10):
        """Lab morale calculator."""
        heronames = [h.strip()
                     for h in ' '.join(heronames).lower().split(',')]

        choices, whitelists = calculator(*heronames, maxteams=maxteams)

        if len(choices) != 1:
            await self.find_optimum_morale(ctx, choices, whitelists)

        else:
            team, first, second = choices[0]
            total = first[0] + second[0]
            lines = [f'> **{total:>2}** morale:']
            for chat in [first, second]:
                gain, name, topic = chat
                topic = ' '.join(topic.split('-')).title()
                lines.append(f'> {gain:>2} from {name.title()} - {topic}')
            body = '\n'.join(lines)

            team = [f'**{t.title()}**' for t in team]
            header = f'> Camping with {conjunctify(team, oxford=False)}:\n'
            await ctx.send(header + body)
            return
