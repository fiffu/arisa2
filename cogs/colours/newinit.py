# -*- coding: utf-8 -*-

import asyncio
from collections import defaultdict
from datetime import datetime, timedelta, timezone
import logging
from random import random, uniform
from types import SimpleNamespace
from typing import Optional

import discord
from discord.ext import commands
from discord.abc import GuildChannel

from appconfig import DEBUGGING
from cogs.mixins import DatabaseCogMixin
from utils.lastreleaselock import AsyncLastReleaseLock, NO_UPDATE
from . import actions
from .config import *


log = logging.getLogger(__name__)


CACHE = defaultdict(dict)


def has_elapsed(tstamp, *args, **kwargs):
    elapsed = datetime.utcnow() - tstamp
    delta = timedelta(*args, **kwargs)
    return elapsed >= delta


def check_value(mutate_or_reroll):
    if mutate_or_reroll not in ['mutate', 'reroll']:
        raise ValueError("argument to 'mutate_or_reroll' must be either "
                         "'mutate' or 'reroll'")


def make_colour_embed(r, g, b, title=None):
    hexa = to_hexcode(r, g, b)
    desc = f'#{hexa} · rgb({r}, {g}, {b})'
    
    colinfo = get_colour_info(r, g, b)
    if colinfo:
        names = ' / '.join('[{}]({})'.format(c['name'], c['url'])
                           for c in colinfo)
        desc += f'\n_{names}_'

    return discord.Embed(title=title,
                         colour=discord.Colour.from_rgb(r, g, b),
                         description=desc)


async def change_colour(member, mutate_or_reroll):
    



class Colours(DatabaseCogMixin, commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    async def get_last(mutate_or_reroll, userid):
        check_value(mutate_or_reroll)

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


    async def update_last(mutate_or_reroll, userid, newtime):
        check_value(mutate_or_reroll)
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
            sql_delete, [memberid, mutate_or_reroll])
        await self.db_execute(
            sql_insert, [memberid, mutate_or_reroll, newtime])


    @commands.command()
    async def col(self, ctx):
        if not ctx.guild:
            await ctx.send(content='This command only works on a server!')
            return

        member = ctx.message.author

        last_reroll = get_last('reroll', member.id)
        proceed = (not last_reroll) or elapsed(last_reroll, **REROLL_COOLDOWN_TIME)

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

        newcol = await change_colour(member, 'reroll')

