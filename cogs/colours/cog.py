# -*- coding: utf-8 -*-

import re
from asyncio import sleep as asleep
from collections import defaultdict
from colorsys import rgb_to_hsv
from datetime import datetime, timedelta, timezone
import logging
from math import ceil
from random import choice, random, uniform
from typing import Optional

import discord
from discord.errors import HTTPException
from discord.ext import commands

from appconfig import DEBUGGING
from cogs.mixins import DatabaseCogMixin
from . import helpers
from .config import *

try:
    from .banners import get_current_banner
except ImportError:
    get_current_banner = lambda: None


log = logging.getLogger(__name__)


CACHE = defaultdict(dict)


VAMPY = '<:vampy:400648781743390720>'
BIRB = '<:birb:508637853593501699>'


def get_role(member):
    for role in member.roles:
        if role.name.lower() == str(member).lower():
            return role

    # Use another loop for 2nd pass looking for a "name role"
    # "Name roles" have names ending with 4-digit discriminators (#1234)
    for role in member.roles:
        if re.match(r"^(.+#\d{4})$", role.name.lower()):
            return role
    return None


def get_max_colour_height(guild) -> Optional[int]:
    for position, role in enumerate(guild.roles):
        if role.name == MAX_HEIGHT_ROLE_NAME:
            return position
    return None


def has_elapsed(tstamp, *args, **kwargs):
    elapsed = datetime.utcnow() - tstamp
    delta = timedelta(*args, **kwargs)
    return elapsed >= delta


def check_valid_action(action):
    acts = ', '.join(['mutate', 'reroll'])
    if action not in acts:
        raise ValueError("value of 'action' must be one of: " + acts)


def make_random_color(h=0, s=0.7, v=0.7):
    """Used in reroll or new colour"""
    banner = get_current_banner()
    if banner:
        h, s, v = banner.roll()
    else:
        h = h or random()
        s = s * uniform(0.8, 1.2)
        v = v * uniform(0.7, 1.3)
    return discord.Colour.from_hsv(h, s, v)


def mutate(*rgb):
    def change():
        step = uniform(0.08, 0.15)  # amount to change by
        sign = choice([1, -1])  # either increase or decrease
        return sign * step

    clamped = helpers.clamp(0, 1)  # make a clamp function witr range [0, 1]
    new = [clamped(x + change()) for x in rgb]

    # log.info('Mutate: rgb(%s %s %s) -> rgb(%s, %s, %s)', *old, *new)
    return new


def make_mutated_color(colobj: discord.Colour):
    rgb = tuple([x / 255 for x in colobj.to_rgb()])
    newrgb = [int(x * 255) for x in mutate(*rgb)]
    return discord.Colour.from_rgb(*newrgb)


def make_colour_embed(r, g, b, title=None, desc=None):
    hexa = helpers.to_hexcode(r, g, b)
    title = title or f'#{hexa} · rgb({r}, {g}, {b})'

    colinfo = helpers.get_colour_name(r, g, b)
    if colinfo and not desc:
        names = ' / '.join('[{}]({})'.format(c['name'], c['url'])
                           for c in colinfo)
        desc = f'\n_{names}_'

    return discord.Embed(title=title,
                         colour=discord.Colour.from_rgb(r, g, b),
                         description=desc)


async def assign_new_colour(member, mutate_or_reroll):
    username = str(member)
    role = get_role(member)

    newcol = make_random_color()
    if mutate_or_reroll is 'mutate':
        if not role:
            return None
        newcol = make_mutated_color(role.colour)

    fmt = 'rgb({}, {}, {})'  # Used in formatting log/audit messages
    new = fmt.format(*newcol.to_rgb())

    attempts = 0

    while attempts < 3:
        try:
            attempts += 1

            # If no role, make new from random colour
            if mutate_or_reroll is 'reroll' and not role:
                log.info('Creating colour role for %s with %s', username, new)
                role = await member.guild.create_role(
                    name=username,
                    colour=newcol,
                    reason='created new colour role as user had none')
                await role.edit(position=get_max_colour_height(member.guild))
                await member.add_roles(role, reason='assign colour role')

            # If have role, update Discord API
            elif mutate_or_reroll in ['reroll', 'mutate']:
                old = fmt.format(*role.colour.to_rgb())
                msg = f"{mutate_or_reroll.title()} new colour {old} -> {new}"
                log.info(msg + ' for %s', username)
                await role.edit(colour=newcol, reason=msg)

            else:
                log.error('Aborting unsupported action: %s', mutate_or_reroll)
                raise NotImplementedError(f'{mutate_or_reroll}')

            return newcol

        except HTTPException as e:
            timeout = min(5, log_http_exception(e))
            await asleep(timeout)

    log.error('Failed to %s for %s after 3 tries', mutate_or_reroll, username)
    return None


def log_http_exception(exc):
    msg = f'{exc.__class__.__name__}'

    resp = exc.response
    timeout = 1  # in seconds

    if resp.status == 429:
        cap = resp.headers.get('X-RateLimit-Limit')
        captype = 'per-route'
        if not cap:
            cap = resp.headers.get('X-RateLimit-Global')
            captype = 'global'
        if not cap:
            captype = 'unknown'

        bucket = resp.headers.get('X-RateLimit-Bucket')

        retry_secs = resp.headers.get('Retry-After') or 0
        timeout = ceil(int(retry_secs) / 1000)

        msg += (f': exceeded {captype} rate limit (bucket: {bucket}) at cap '
                f'of {cap} while editing colour, retrying in: {timeout}s')
        log.error(msg)

        tiemout = retry_secs

    else:
        log.error(msg)

    return timeout


def cooldown_remaining(last_use_tstamp, **cooldown_timedelta_kwargs):
    cooldown_end = last_use_tstamp + timedelta(**REROLL_COOLDOWN_TIME)
    cooldown_to_go = cooldown_end - datetime.utcnow()
    total_secs = cooldown_to_go.total_seconds()

    if max(total_secs, 0) == 0:
        return None

    hours, remainder = divmod(total_secs, 60 * 60)
    mins, secs = divmod(remainder, 60)
    h = f'{int(hours)}hr ' if int(hours) else ''
    m = f'{int(mins)}min ' if int(mins) else ''
    s = '' if any([h, m]) else f'cooldown: {secs:.2f} sec '
    hms = f'{h}{m}{s}'.strip()
    return hms


class Colours(DatabaseCogMixin, commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    async def update_cache(self, userid):
        sql_select = """SELECT * FROM colours WHERE userid = %s"""
        rows = await self.db_query(sql_select, [userid])
        if not rows:
            return None

        for key in ['mutate', 'reroll', 'is_frozen']:
            CACHE[userid][key] = None

        for row in rows:
            action = row['mutateorreroll']
            CACHE[userid][action] = row['tstamp']

            if action == 'mutate':
                # don't use `is` as the predicate for this block!
                # `==` compares equality, `is` compares identity
                CACHE[userid]['is_frozen'] = row['is_frozen']


    async def update_last(self, mutate_or_reroll, userid, newtime):
        check_valid_action(mutate_or_reroll)

        # Upsert the new time
        sql_delete = f"""DELETE FROM colours
                         WHERE userid = %s AND mutateorreroll = %s"""
        sql_insert = f"""INSERT INTO colours
                             (userid, mutateorreroll, tstamp)
                         VALUES (%s, %s, %s)"""

        # Warning: these execute in autocommit so they're not atomic, but
        # if one fails the other should fail too (barring syntax errors)
        await self.db_execute(
            sql_delete, [userid, mutate_or_reroll])
        await self.db_execute(
            sql_insert, [userid, mutate_or_reroll, newtime])

        await self.update_cache(userid)


    async def update_frozen(self, userid, set_to):
        # Update row and local cache
        sql_update = f"""UPDATE colours SET is_frozen = %s
                         WHERE userid = %s AND mutateorreroll = %s"""
        await self.db_query(sql_update, [set_to, userid, 'mutate'])
        await self.update_cache(userid)


    async def get_last(self, mutate_or_reroll, userid):
        check_valid_action(mutate_or_reroll)

        if userid in CACHE:
            return CACHE[userid].get(mutate_or_reroll)

        await self.update_cache(userid)
        return CACHE[userid].get(mutate_or_reroll)


    async def get_is_frozen(self, userid):
        if userid in CACHE:
            return CACHE[userid].get('is_frozen')

        await self.update_cache(userid)
        return CACHE[userid].get('is_frozen')


    @commands.command()
    async def col(self, ctx):
        """Gives you a shiny new colour"""
        if not ctx.guild:
            await ctx.send('This command only works on a server!')
            return

        member = ctx.message.author

        last_reroll = await self.get_last('reroll', member.id)
        cooled_down = False
        if last_reroll:
            cooled_down = has_elapsed(last_reroll, **REROLL_COOLDOWN_TIME)

        proceed = (not last_reroll) or cooled_down

        if not proceed:
            # Bump remaining reroll cooldown, capping at 2x of max reroll time
            last_reroll = min(
                last_reroll + 2 * timedelta(**REROLL_COOLDOWN_TIME),
                last_reroll + timedelta(**REROLL_PENALTY_TIME)
            )
            await self.update_last('reroll', member.id, last_reroll)

            # Parse remaining cooldown into human-friendly timestamp
            hms = cooldown_remaining(last_reroll, **REROLL_COOLDOWN_TIME)
            u = '' if random() < 0.5 else 'u'
            msg = f'You cannot reroll a new colo{u}r yet! ({hms})'
            await ctx.send(content=msg)
            log.info('Blocked reroll from %s due to cooldown (%s remain)',
                     str(member),
                     hms)
            return

        newcol = await assign_new_colour(member, 'reroll')
        if not newcol:
            msg = ("I couldn't assign you a new colour. This could be due to "
                   "Discord's rate limits, so try again later.")
            await ctx.send(content=msg)
            return

        embed = make_colour_embed(*newcol.to_rgb())
        now = datetime.utcnow()
        await self.update_last('mutate', member.id, now)
        await self.update_last('reroll', member.id, now)
        await ctx.send(content=None, embed=embed)


    async def set_freeze(self, ctx, set_to: bool):
        if not ctx.guild:
            await ctx.send('This command only works on a server!')
            return

        member = ctx.message.author
        role = get_role(member)
        un = 'un' if set_to is False else ''

        if not role:
            await ctx.send("You don't even have a colour role...")
            return

        already_frozen = await self.get_is_frozen(member.id)
        if set_to == already_frozen:
            await ctx.send(f'Your colour has already been {un}frozen.')
            return

        embed = make_colour_embed(*role.colour.to_rgb()) if set_to else None

        if role.name.lower() == 'tannu#2037':
            # Using rolename rather than username is more "tamper-resistant"
            # since users can't change or remove their colour roles (for now)
            if set_to:
                embed = None
            else:
                # emoji = choice([VAMPY, BIRB])
                # await ctx.send(emoji)
                return

        log.info('Set %sfreeze on %s', un, str(member))
        await self.update_frozen(member.id, set_to)


        await ctx.send(f'Your colour has been {un}frozen.', embed=embed)


    @commands.command()
    async def freeze(self, ctx):
        """Stops your colour from mutating"""
        await self.set_freeze(ctx, set_to=True)


    @commands.command()
    async def unfreeze(self, ctx):
        """Makes your colour start mutating"""
        await self.set_freeze(ctx, set_to=False)


    @commands.command(aliases=['ci'])
    async def colinfo(self, ctx):
        """Tells you about your colour"""
        if not ctx.guild:
            await ctx.send('This command only works on a server!')
            return

        member = ctx.message.author
        role = get_role(member)

        if not role:
            await ctx.send("You don't have a colour role. Type !col to get "
                           "a random colour!")
            return

        colour = role.colour
        embed = make_colour_embed(*colour.to_rgb())

        desc = embed.description or ''
        desclines = [desc]

        last_reroll = await self.get_last('reroll', member.id)
        cd_to_go = cooldown_remaining(last_reroll, **REROLL_COOLDOWN_TIME)
        cd_to_go = cd_to_go or '_(No cooldown, reroll available)_'

        desclines.extend(['\n\n' if desc else '',
                          '**Reroll cooldown: **',
                          cd_to_go])

        last_mutate = await self.get_last('mutate', member.id)
        h, m, day, mth, yr = last_mutate.strftime('%H %M %d %b %Y').split()

        now = datetime.utcnow()
        now_day, now_mth, now_yr = now.strftime('%d %b %Y').split()
        year = '' if yr == now_yr else ' ' + yr  # Hide year if it's this year

        date, daysago = '', ''
        if (day == now_day) and (mth == now_mth) and (yr == now_yr):
            date = 'Today'
        else:
            date = f'{int(day)} {mth}{year}'
            days_diff = (now - last_mutate).days
            if days_diff > 1:
                daysago = f', {days_diff} days ago'

        desclines.extend(['\n',
                          '**Last mutate: **',
                          f'{date} at {h}:{m} UTC{daysago}'])

        frozen = await self.get_is_frozen(member.id)
        desclines.extend([' _(currently frozen)_' if frozen else ''])


        if ctx.message.content.startswith(ctx.prefix + 'colinfo'):
            protip = 'Protip: you can use !ci as a shortcut for this command.'
            # desclines.extend(
            #     ['\n', f'`{protip}`'])
            embed.set_footer(text=protip)

        embed.description = ''.join(desclines)

        await ctx.send(embed=embed)


    @commands.Cog.listener()
    async def on_message(self, message):
        # Ignore messages from self, or from non-guild channels
        if self.bot.user.id == message.author.id or not message.guild:
            return

        # Block mutation from command invocations
        # Seems to lead to race conditions causing interference in
        # executing some commands (such as !uncol)
        if message.content.startswith(self.bot.command_prefix):
            return

        member = message.author

        if not get_role(member):
            return

        last_mutate = await self.get_last('mutate', member.id)

        # If mutated before, only proceed if cooldown has elapsed
        if last_mutate:
            if not has_elapsed(last_mutate, **MUTATE_COOLDOWN_TIME):
                return
            # 10% chance to mutate if off cooldown
            elif random() < 0.9:
                return

        # If never mutated before, 20% chance per msg to start mutation
        else:
            if random() < 0.2:
                return


        frozen = await self.get_is_frozen(member.id)
        if frozen:
            return

        newcol = await assign_new_colour(member, 'mutate')

        if not newcol:
            return

        await self.update_last('mutate', member.id, datetime.utcnow())
        rgbstr = 'rgb({}, {}, {})'.format(*newcol.to_rgb())
        log.info('Updated mutate time -> %s for %s', rgbstr, str(member))
