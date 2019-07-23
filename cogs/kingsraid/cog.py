# -*- coding: utf-8 -*-

import logging
import unicodedata as ud
from types import SimpleNamespace

import discord
from discord.ext import commands

import appconfig
from . import model as kr

DEBUGGING = appconfig.DEBUGGING
NOT_FOUND = "Sorry! I couldn't find anything called `{}`. Try something else?"

PAGES_EMOJI = {
    0: ud.lookup('LEFT-POINTING MAGNIFYING GLASS'),
    1: ud.lookup('DIGIT ONE') + ud.lookup('COMBINING ENCLOSING KEYCAP'),
    2: ud.lookup('DIGIT TWO') + ud.lookup('COMBINING ENCLOSING KEYCAP'),
    3: ud.lookup('DIGIT THREE') + ud.lookup('COMBINING ENCLOSING KEYCAP'),
    4: ud.lookup('DIGIT FOUR') + ud.lookup('COMBINING ENCLOSING KEYCAP'),
    5: ud.lookup('SCROLL')
}



def create_embed_template(obj):
    title = f'{obj.name}'
    if obj.entity is 'Artifact':
        descs = ['Artifact']
    else:
        descs = [d.title() for d in (
            getattr(obj, "class"),
            obj.type,
            obj.position['type']
        )]

    embed = discord.Embed(title=title, url=obj.mogurl)

    desc = '_' + ' · '.join(descs) + '_'
    embed.description = desc
    footer_text = ('Click reactions for more pages · '
                   'Data from maskofgoblin.com')
    embed.set_footer(text=footer_text)

    try:
        embed.set_thumbnail(url=obj.iconurl)
    except AttributeError:
        pass
    return embed


def create_embed(obj, page=0):
    def zero_five_stars(li):
        s = f'**`0*:`** {li[0]}\n**`3*:`** {li[3]}\n**`5*:`** {li[5]}'
        # Monkey patch for excess length
        if len(s) > 1024:
            s = f'**`0*:`** {li[0]}\n**`3*:`** {li[3]}'
        return s

    def calc_mp_consumption():
        def find_lcm(*nums):
            if not nums:
                return 0
            nums = [n for n in nums if type(n) is int and n > 0]
            *others, big = sorted(nums)
            factor = 1
            lcm = big * factor
            while any(lcm % x for x in others):
                factor += 1
                lcm = big * factor
            return lcm, [lcm // x for x in nums]
        skills = [obj.data[f's{i}'] for i in [1, 2, 3]]
        cds = [s.get('cooldown', 0) for s in skills]
        manas = [s.get('mana', 0) for s in skills]
        if not any(manas):
            return 0, 0, 0
        total_cast_time, iters = find_lcm(*cds)
        total_mana_cost = 0
        for i, cast_cnt in enumerate(iters):
            total_mana_cost += cast_cnt * manas[i] * 1000
        avg_mana_spend = total_mana_cost / total_cast_time
        return avg_mana_spend, total_mana_cost, total_cast_time

    def make_basic_sections():
        d = obj.data

        t5 = f"**[Light] {obj.t5['light']}\n[Dark] {obj.t5['dark']}**"
        aa = (f"{obj.auto['duration']} sec per cycle, hit clusters:\n"
              f"`{obj.auto['clusters']}`")
        # ['time'] is list of clusters (lists); 1 cluster = full mpatk gain
        cycle_mpatk = d['mpatk'] * len(obj.auto['time'])  # mpatk * clusters
        base_mp_rate = cycle_mpatk / obj.auto['duration'] + d['mpsec']
        orb = 1000 / base_mp_rate
        mana_avg, _, _ = calc_mp_consumption()
        mp = (f"{d['mpatk']} MP/attack, {d['mpsec']} MP/sec\n"
              f"Effective regen: "
              f"`{int(base_mp_rate)} MP/sec ({orb:.2f} sec/orb)`\n"
              f"Base consumption: `{mana_avg:.2f} MP/sec`")

        sections = [
            ('Transcendence 5', t5),
            (obj.uw['name'], zero_five_stars(obj.uw['description'])),
            # True for inline fields
            ('Base MP regen', mp, True),
            ('Autoattack pattern', aa, True)
        ]
        return sections

    def formatted_skill_info(skillnum):
        sn = f's{skillnum}'
        skill = getattr(obj, sn)
        skilldata = obj.data[sn]

        s = dict()
        s['name'] = f"S{skillnum}: {skill['name']}"
        s['description'] = skill['description'].replace('???', '`???`')

        s['mana'] = skilldata.get('mana') or '(no mana cost)'
        s['cooldown'] = str(skilldata.get('cooldown', 'Passive'))
        if type(s['mana']) is int:
            s['mana'] = s['mana'] * ud.lookup('BLACK HEXAGON')

        s['transcends'] = "**[Light] {}\n[Dark] {}**".format(
            skill['light'], skill['dark'])

        lang, token = [
            ('html', '#'),
            ('diff', '+'),
            ('md', '#'),
            ('glsl', '#')
        ][skillnum - 1]

        s['books'] = f'```{lang}\n' + '\n'.join([
            f'{token} {cost:>3}: {effect}'
            for (cost, effect)
            in zip([20, 60, 120], skill['books'])
        ]) + '```'

        if skill.get('ut'):
            # Add key 'ut': Tuple[name, desc]
            desc = [s.split(']', 1)[-1].strip()
                for s in skill['ut']['description']]
            s['ut'] = (
                f'UT{skillnum}: ' + skill['ut']['name'],
                zero_five_stars(desc)
            )
        else:
            s['ut'] = None

        linked = skill.get('linked')
        if linked:
            # Add key 'linked': Tuple[name, desc]
            name = linked['name']
            desc = linked['description'].replace('???', '`???`')
            s['linked'] = ('Linked: ' + name, desc)
        else:
            s['linked'] = None

        return SimpleNamespace(**s)


    def make_skills_sections(skillnum):
        s = formatted_skill_info(skillnum)
        if s.cooldown == 'Passive':
            title = ' · '.join([s.name, s.cooldown])
        else:
            title = ' · '.join([s.name, s.mana, s.cooldown + ' sec CD'])

        sections = [(f'__{title}__', s.description)]

        if s.linked:
            sections.append(s.linked)

        sections.append(('Upgrades:', s.transcends + '\n' + s.books))

        if s.ut:
            sections.append(s.ut)

        return sections


    def make_story_sections():
        sections = []
        if obj.entity is 'Hero':
            sections.append((obj.subtitle, obj.description))

        sections.append(('Story', obj.story))

        return sections


    embed = create_embed_template(obj)
    if obj.entity == 'Artifact' and page != 5:
        embed.description += ('\n' + zero_five_stars(obj.description))
        return embed
    if page not in PAGES_EMOJI.keys():
        return None

    sections = []
    # basic info
    if page == 0:
        sections = make_basic_sections()

    # Skills pages
    elif page in [1, 2, 3, 4]:
        sections = make_skills_sections(skillnum=page)

    # Bio and portrait
    elif page == 5:
        sections = make_story_sections()
        try:
            embed.set_image(url=obj.portraiturl)
        except AttributeError:
            # Fails on artifacts (they have no portraiturl attrib)
            pass

    for (k, v, *others) in sections:
        use_inline = bool(others)
        embed.add_field(name=f'__{k}__', value=v, inline=use_inline)
    return embed



class KrSearch(commands.Cog):
    """
    Cog that defines bot.on_ready behaviour
    """
    log = logging.getLogger(__name__)

    def __init__(self, bot):
        self.bot = bot
        self._autoupdate = (not DEBUGGING)


    @property
    def autoupdate(self):
        return self._autoupdate


    @autoupdate.setter
    def autoupdate(self, value=True):
        self._autoupdate = bool(value)


    def is_me(self, user):
        return self.bot.user.id == user.id


    def is_my_message(self, message):
        return self.is_me(message.author)


    def is_kr_embed(self, message):
        embeds = message.embeds
        if len(embeds) < 1:
            return False
        embed = embeds[0]
        return embed.url and embed.url.startswith('https://maskofgoblin.com')


    def no_own_reacts(self, message):
        reacts = [r for r in message.reactions if r in PAGES_EMOJI.values()]
        return (not reacts)


    @commands.Cog.listener()
    async def on_ready(self):
        if not self._autoupdate:
            self.log.warning('Autoupdate was cancelled{}.'.format(
                ' (running in debug mode)' if DEBUGGING else ''))
            return
        await kr.update(self.bot.loop)
        self.log.info('Autoupdate complete')


    @commands.Cog.listener()
    async def on_message(self, message):
        if not (self.is_my_message(message)
                and self.is_kr_embed(message)
                and self.no_own_reacts(message)):
            return

        embed = message.embeds[0]

        emoji_to_add = (0, 5)
        if '/hero/' in embed.url:
            emoji_to_add = (0, 1, 2, 3, 4, 5)

        for emoji in [PAGES_EMOJI[i] for i in emoji_to_add]:
            await message.add_reaction(emoji)


    async def change_page(self, reaction, user):
        if self.is_me(user):
            return

        if not (self.is_my_message(reaction.message)
                and self.is_kr_embed(reaction.message)):
            return

        embed = reaction.message.embeds[0]

        entity = kr.search(embed.title)
        if not (embed.title and entity):
            return

        for page, emoji in PAGES_EMOJI.items():
            if emoji == reaction.emoji:
                new = create_embed(entity, page)

        await reaction.message.edit(embed=new)


    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        await self.change_page(reaction, user)


    @commands.Cog.listener()
    async def on_reaction_remove(self, reaction, user):
        await self.change_page(reaction, user)


    @commands.command()
    async def kr(self, ctx, name: str):
        """Looks up a hero or artifact in King's Raid"""
        entity = kr.search(name)
        if not entity:
            ctx.send(NOT_FOUND)
        else:
            embed = create_embed(entity)
            await ctx.send(content=None, embed=embed)
