# -*- coding: utf-8 -*-

import asyncio
from collections import defaultdict
from datetime import datetime, timedelta, timezone
import logging
from math import ceil
from random import random, uniform
from types import SimpleNamespace
from typing import Optional

import discord
from discord.errors import HTTPException
from discord.ext import commands

from appconfig import DEBUGGING
from cogs.mixins import DatabaseCogMixin
from . import actions
from .config import *


log = logging.getLogger(__name__)


CACHE = defaultdict(dict)


def get_role(member):
    for role in member.roles:
        if role.name.lower() == str(member).lower():
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


def make_random_color(h=0, s=0.5, v=0.8):
    s = s * uniform(0.9,1.1)
    v = v * uniform(0.9,1.1)
    h, s, v = actions.mutate_hsv(h or random(), s, v, repeats=0)
    return discord.Colour.from_hsv(h, s, v)


def make_colour_embed(r, g, b, title=None):
    hexa = to_hexcode(r, g, b)
    desc = f'#{hexa} · rgb({r}, {g}, {b})'

    colinfo = get_colour_name(r, g, b)
    if colinfo:
        names = ' / '.join('[{}]({})'.format(c['name'], c['url'])
                           for c in colinfo)
        desc += f'\n_{names}_'

    return discord.Embed(title=title,
                         colour=discord.Colour.from_rgb(r, g, b),
                         description=desc)


async def assign_new_colour(member, mutate_or_reroll):
    username = str(member)
    role = get_role(member)
    colour = make_random_color()

    fail_count = 0

    # If no role, make new from random colour
    while fail_count < 5:
        try:
            if not role:
                role = await member.guild.create_role(
                    name=username,
                    colour=colour,
                    reason='created new colour role as user had none')
                await role.edit(position=get_max_colour_height(member.guild))
                await member.add_roles(role, reason='assign colour role')

            elif mutate_or_reroll is 'reroll':
                oldcol = 'rgb({}, {}, {})'.format(*role.colour.to_rgb())
                await role.edit(colour=colour,
                                reason=f"Reroll new colour, was: {oldcol}")

            elif mutate_or_reroll is 'mutate':
                raise NotImplementedError

        except HTTPException as e:
            msg = f'{e.__class__.__name__}: {str(e)}'

            if e.response.status is 429:
                cap = e.response.headers.get('X-RateLimit-Limit')
                retry = e.response.headers.get('Retry-After') or 0
                retry_secs = ceil(retry * 1000)
                msg += (f' (rate limit while assigning colour ({cap}), '
                        f' retry: {retry_secs}s')
                log.error(msg)
                fail_count += 1
                await asyncio.sleep(retry_secs)

            else:
                log.error(msg)

    return colour


class Colours(DatabaseCogMixin, commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    async def get_last(self, mutate_or_reroll, userid):
        check_valid_action(mutate_or_reroll)

        if userid in CACHE:
            return CACHE[userid].get(mutate_or_reroll)

        sql_select = """SELECT * FROM colours
                        WHERE userid = %s AND mutateorreroll = %s"""
        rows = await self.db_query(sql_select, [userid, mutate_or_reroll])
        if rows:
            lasttime = rows[0]['tstamp']
            CACHE[userid][mutate_or_reroll] = lasttime
            return lasttime

        return None


    async def update_last(self, mutate_or_reroll, userid, newtime):
        check_valid_action(mutate_or_reroll)
        CACHE[userid][mutate_or_reroll] = newtime

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


    @commands.command()
    async def col(self, ctx):
        if not ctx.guild:
            await ctx.send(content='This command only works on a server!')
            return

        member = ctx.message.author

        last_reroll = await self.get_last('reroll', member.id)
        cooled_down = has_elapsed(last_reroll, **REROLL_COOLDOWN_TIME)
        proceed = (not last_reroll) or cooled_down

        if not proceed:
            cooldown_to_go = timedelta(**REROLL_COOLDOWN_TIME) - last_reroll
            hours, remainder = divmod(cooldown_to_go.total_seconds(), 60 * 60)
            mins, secs = divmod(remainder, 60)
            h = f'{int(hours)}hr ' if int(hours) else ''
            m = f'{int(mins)}min ' if int(mins) else ''
            s = '' if any([h, m]) else f'cooldown: {secs:.2f} sec '
            hms = f'{h}{m}{s}'.strip()
            u = '' if random() < 0.5 else 'u'
            msg = f'You cannot reroll a new colo{u}r yet! ({hms})'
            await ctx.send(content=msg)
            return

        newcol = await assign_new_colour(member, 'reroll')
        embed = make_colour_embed(*newcol.to_rgb())
        await self.update_last('reroll', member.id, datetime.now())
        await ctx.send(content=None, embed=embed)
