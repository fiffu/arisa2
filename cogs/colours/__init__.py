# -*- coding: utf-8 -*-

import asyncio
from collections import defaultdict
from datetime import datetime, timedelta
import logging
from random import random
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


# Use a cache factory makes it clear that two locks are created per key,
# instead of two lock instances being shared across keys
def locks_factory():
    return SimpleNamespace(
        mutate=AsyncLastReleaseLock(),
        reroll=AsyncLastReleaseLock()
    )
CACHE = defaultdict(locks_factory)



def make_random_color(h=0, s=0.5, v=0.8):
    h, s, v = actions.mutate_hsv(h or random(), s, v, repeats=0)
    return discord.Colour.from_hsv(h, s, v)


def get_role(member):
    for role in member.roles:
        if role.name.lower() == str(member).lower():
            return role
    return None


async def mutate_role_colour(role: discord.Role, repeats=1):
    r, g, b = role.colour.to_rgb()
    r, g, b = [x / 255 for x in (r, g, b)]
    r, g, b = actions.mutate_rgb(r, g, b, repeats=repeats)
    r, g, b = [int(x * 255) for x in (r, g, b)]
    newcol = discord.Colour.from_rgb(r, g, b)
    return newcol



def get_max_colour_height(guild) -> Optional[int]:
    for position, role in enumerate(guild.roles):
        if role.name == MAX_HEIGHT_ROLE_NAME:
            return position
    return None


async def setup_roles(guild):
    if get_max_colour_height(guild) is None:
        log.info('Setting up new colour role height limit for guild %s',
                 guild.name)
        await guild.create_role(name=MAX_HEIGHT_ROLE_NAME,
                                colour=0xff0000,
                                reason='Setup max height for colour roles')


class Colours(DatabaseCogMixin, commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    @commands.Cog.listener()
    async def on_ready(self):
        for guild in self.bot.guilds:
            await setup_roles(guild)

        await super().on_ready()


    async def _adjust_colour(self, member, msgable, repeats=1, verbose=False):
        if self.bot.user.id == member.id:
            return

        username = str(member)
        role = get_role(member)
        colour = None

        if not role:
            colour = make_random_color()
            role = await member.guild.create_role(
                name=username,
                colour=colour,
                reason='created new colour role as user had none')
            await role.edit(position=get_max_colour_height(member.guild))
            await member.add_roles(role, reason='assign colour role')
        else:
            colour = await mutate_role_colour(role, repeats=repeats)
            oldcol = 'rgb({}, {}, {})'.format(*role.colour.to_rgb())
            await role.edit(
                colour=colour,
                reason=f'Mutate colour {repeats} steps, was: {oldcol}'
            )

        if verbose:
            r, g, b = colour.to_rgb()
            hexa = ''.join(f'{hex(n)[2:]:>02}' for n in [r, g, b])
            embed = discord.Embed(title=f'#{hexa} · rgb({r}, {g}, {b})',
                                  colour=colour)
            content = verbose if isinstance(verbose, str) else None
            await msgable.send(content=content, embed=embed)


    async def update_db(self,
                        memberid: int,
                        mutate_or_reroll,
                        lock: AsyncLastReleaseLock):

        async def _update(newtime):
            cooldown = dict(mutate=MUTATE_COOLDOWN_TIME,
                            reroll=REROLL_COOLDOWN_TIME)[mutate_or_reroll]

            await lock.acquire()

            sql_get = f"""SELECT tstamp FROM colours
                          WHERE userid = %s AND mutateorreroll = %s"""
            rows = await self.db_query(sql_get, [memberid, mutate_or_reroll])

            proceed = False
            lasttime = None
            if rows:
                # Extra check on time-since-last-release viz. database records
                lasttime = rows[0]['tstamp']
                if (newtime - lasttime) > timedelta(**cooldown):
                    proceed = True
            else:
                proceed = True

            if not proceed:
                # Release and cache the more recent time from the db
                lock.release(lasttime)
                return

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

            # Release and cache the provided timestamp if all goes well
            lock.release(newtime)

        newtime = datetime.now()
        if mutate_or_reroll not in ['mutate', 'reroll']:
            raise ValueError("arg 'mutate_or_reroll' must be either "
                             "str('mutate') or str('reroll')")

        try:
            await asyncio.wait_for(_update(newtime), DB_UPDATE_TIMEOUT_SECS)
        except asyncio.TimeoutError:
            log.error(f'DB update timed out (set {mutate_or_reroll} for '
                      f'memberid {memberid} to time {newtime}')
            newtime = NO_UPDATE  #  ensure lock's cached time won't be updated
        finally:
            if lock.locked():
                lock.release(time=newtime)


    @commands.command()
    async def col(self, ctx):
        if not ctx.guild:
            await ctx.send(content='This command only works on a server!')
            return

        member = ctx.message.author

        lock = CACHE[member.id].reroll
        oldtime = lock.time or datetime(year=1970, month=1, day=1)

        if lock.elapsed(**REROLL_COOLDOWN_TIME):
            await self.update_db(member.id, 'reroll', lock)

        # Test if lock.time increased, indicating successful update
        updated = False
        if lock.time and (lock.time > oldtime):
            updated = True

        if not updated:
            await ctx.send(content='You cannot reroll a new colour yet!')
        else:
            await self._adjust_colour(
                member, ctx, repeats=20, verbose=DEBUGGING and 'Rerolled')


    @commands.command()
    async def uncol(self, ctx):
        if not DEBUGGING:
            return

        if not ctx.guild:
            await ctx.send(content='This command only works on a server!')
            return

        role = get_role(ctx.message.author)
        if role:
            await role.delete()


    @commands.Cog.listener()
    async def on_message(self, message):
        if self.bot.user.id == message.author.id:
            # Don't colorize self
            return

        if message.content.startswith(self.bot.command_prefix):
            # Block mutation from command invocations
            # Seems to lead to race conditions causing interference in
            # executing some commands (such as !uncol)
            return

        if not message.guild:
            return

        member = message.author

        if not get_role(member):
            return

        lock = CACHE[member.id].mutate
        oldtime = lock.time or datetime(year=1970, month=1, day=1)
        if lock.elapsed(**MUTATE_COOLDOWN_TIME):
            await self.update_db(member.id, 'mutate', lock)

        # Test if lock.time increased, indicating successful update
        updated = False
        if lock.time and (lock.time > oldtime):
            updated = True

        if updated:
            await self._adjust_colour(
                member,
                message.channel,
                repeats=1,
                verbose=DEBUGGING and 'Mutated')


    @commands.command()
    async def color(self, ctx):
        await self.col(ctx)


    @commands.command()
    async def colour(self, ctx):
        await self.col(ctx)


    @commands.command()
    async def cool(self, ctx):
        if not ctx.guild:
            return

        member = ctx.author
        locks = CACHE[member.id]
        await ctx.send(content=
            f'Mutate: {str(locks.mutate.time)}, '
            f'usable={locks.mutate.elapsed(**MUTATE_COOLDOWN_TIME)}\n'
            f'Reroll: {str(locks.reroll.time)}, '
            f'usable={locks.reroll.elapsed(**REROLL_COOLDOWN_TIME)}')


    @commands.command()
    async def colyank(self, ctx):
        guild = ctx.guild

        if not guild:
            await ctx.send(content='This command only works on a server!')
            return

        async with ctx.typing():
            await setup_roles(guild)
            max_height = get_max_colour_height(guild)
            guild_member_names = [str(m) for m in guild.members]
            for role in ctx.guild.roles.copy():
                if role.name not in guild_member_names:
                    continue
                await role.edit(
                    position=max_height,
                    reason='!colyank: moving to anchor height')
