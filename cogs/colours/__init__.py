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


# Use a cache factory makes it clear that two locks are created per key,
# instead of two lock instances being shared across keys
def locks_factory():
    return SimpleNamespace(
        mutate=AsyncLastReleaseLock(),
        reroll=AsyncLastReleaseLock()
    )
CACHE = defaultdict(locks_factory)




def make_random_color(h=0, s=0.5, v=0.8):
    s = s * uniform(0.9,1.1)
    v = v * uniform(0.9,1.1)
    h, s, v = actions.mutate_hsv(h or random(), s, v, repeats=0)
    return discord.Colour.from_hsv(h, s, v)


def get_role(member):
    for role in member.roles:
        if role.name.lower() == str(member).lower():
            return role
    return None


async def mutate_role_colour(role: discord.Role, steps=1):
    r, g, b = role.colour.to_rgb()
    r, g, b = [x / 255 for x in (r, g, b)]
    r, g, b = actions.mutate_rgb(r, g, b, repeats=steps)
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


    async def _adjust_colour(self, member, msgable, steps=1, verbose=False):
        if self.bot.user.id == member.id:
            return

        username = str(member)
        role = get_role(member)
        colour = None

        # If no role, make new from random colour
        if not role:
            colour = make_random_color()
            role = await member.guild.create_role(
                name=username,
                colour=colour,
                reason='created new colour role as user had none')
            await role.edit(position=get_max_colour_height(member.guild))
            await member.add_roles(role, reason='assign colour role')

        # Mutate by `steps` steps
        else:
            oldcol = 'rgb({}, {}, {})'.format(*role.colour.to_rgb())
            reason = f'Mutate colour {steps} steps, was: {oldcol}'
            if steps == 0:
                colour = make_random_color()
                reason = f"Reroll new colour, was: {oldcol}"
            else:
                colour = await mutate_role_colour(role, steps=steps)
            await role.edit(
                colour=colour,
                reason=reason
            )

        if verbose:
            r, g, b = colour.to_rgb()
            hexa = to_hexcode(r, g, b)
            embed = discord.Embed(title=f'#{hexa} · rgb({r}, {g}, {b})',
                                  colour=colour)
            content = verbose if isinstance(verbose, str) else None
            await msgable.send(content=content, embed=embed)


    async def _freeze_colour(self, member, msgable, set_to=True):
        role = get_role(member)

        if not role:
            await msgable.send("You don't even have a colour role...")
            return

        await self.db_freeze_colour(member.id, set_to)

        if set_to == True:
            r, g, b = role.colour.to_rgb()
            hexa = to_hexcode(r, g, b)
            content = "Your colour has been locked to:"
            embed = discord.Embed(title=f'#{hexa} · rgb({r}, {g}, {b})',
                                  colour=role.colour)
            await msgable.send(content=content, embed=embed)
        else:
            await msgable.send(content="Enabled mutation for your colour.")


    async def _is_colour_mutable(self, memberid: int) -> bool:
        sql_isfrozen = """SELECT * FROM colours
                          WHERE userid = %s AND mutateorreroll = %s
                          AND is_frozen = %s"""
        rows = await self.db_query(sql_isfrozen,
                                   [memberid, 'mutate', True])

        return True if rows else False


    async def db_adjust_colour(self,
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
                proceed = False

            if not proceed:
                # Release and cache the more recent time from the db
                lock.release(lasttime)
                return False

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
            return True

        newtime = datetime.utcnow()
        if mutate_or_reroll not in ['mutate', 'reroll']:
            raise ValueError("arg 'mutate_or_reroll' must be either "
                             "str('mutate') or str('reroll')")

        try:
            return await asyncio.wait_for(
                _update(newtime), DB_UPDATE_TIMEOUT_SECS)
        except asyncio.TimeoutError:
            log.error(f'DB update timed out (set {mutate_or_reroll} for '
                      f'memberid {memberid} to time {newtime})')
            newtime = NO_UPDATE  #  ensure lock's cached time won't be updated
        finally:
            if lock.locked():
                lock.release(time=newtime)
        return False


    async def db_freeze_colour(self, memberid: int, set_to: bool) -> bool:
        sql_get = f"""SELECT * FROM colours WHERE userid = %s"""
        rows = await self.db_query(sql_get, [memberid])

        if not rows:
            return False

        last_mutate = None
        for row in rows:
            if row['mutateorreroll'] == 'mutate':
                last_mutate = row['tstamp']

        # Update row if there's a record of last mutate time,
        if last_mutate:
            sql_update = f"""UPDATE colours SET is_frozen = %s
                             WHERE userid = %s AND mutateorreroll = %s"""
            await self.db_query(sql_update, [set_to, memberid, 'mutate'])

        # or insert new row if there's no record
        else:
            newtime = datetime.utcnow()
            sql_insert = f"""INSERT INTO colours
                                 (userid, mutateorreroll, tstamp, is_frozen)
                             VALUES (%s, %s, %s, %s)"""
            await self.db_execute(
                sql_insert, [memberid, 'mutate', newtime, True])

        return True


    @commands.command()
    async def col(self, ctx):
        if not ctx.guild:
            await ctx.send(content='This command only works on a server!')
            return

        await ctx.trigger_typing()
        member = ctx.message.author

        lock = CACHE[member.id].reroll
        proceed = False

        if lock.elapsed(**REROLL_COOLDOWN_TIME):
            proceed = await self.db_adjust_colour(member.id, 'reroll', lock)

        # Test again if cooldown elapsed
        if not proceed:
            delta_cooldown = timedelta(**REROLL_COOLDOWN_TIME)
            delta_remain = delta_cooldown - lock.time_since_last_release()
            hours, remainder = divmod(delta_remain.total_seconds(), 60 * 60)
            mins, secs = divmod(remainder, 60)
            h = f'{int(hours)}hr ' if int(hours) else ''
            m = f'{int(mins)}min ' if int(mins) else ''
            s = '' if any([h, m]) else f'cooldown: {secs:.2f} sec '
            hms = f'{h}{m}{s}'.strip()
            u = '' if random() < 0.5 else 'u'
            msg = f'You cannot reroll a new colo{u}r yet! ({hms})'
            await ctx.send(content=msg)

        else:
            await self._adjust_colour(
                member, ctx, steps=0, verbose='Rolled new colour:')


    @commands.command()
    async def freeze(self, ctx):
        if not ctx.guild:
            await ctx.send(content='This command only works on a server!')
            return

        await ctx.trigger_typing()
        member = ctx.message.author
        await self._freeze_colour(member, ctx, set_to=True)


    @commands.command()
    async def unfreeze(self, ctx):
        if not ctx.guild:
            await ctx.send(content='This command only works on a server!')
            return

        member = ctx.message.author
        await self._freeze_colour(member, ctx, set_to=False)


    # @commands.command()
    # async def uncol(self, ctx):
    #     if not DEBUGGING:
    #         return

    #     if not ctx.guild:
    #         await ctx.send(content='This command only works on a server!')
    #         return

    #     role = get_role(ctx.message.author)
    #     if role:
    #         await role.delete()


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

        mutable = await self._is_colour_mutable(member.id)
        if not mutable:
            return

        lock = CACHE[member.id].mutate
        oldtime = lock.time or datetime(year=1970, month=1, day=1)
        if lock.elapsed(**MUTATE_COOLDOWN_TIME):
            await self.db_adjust_colour(member.id, 'mutate', lock)

        # Test if lock.time increased, indicating successful update
        updated = False
        if lock.time and (lock.time > oldtime):
            updated = True

        if updated:
            await self._adjust_colour(
                member,
                message.channel,
                steps=1,
                verbose=DEBUGGING and 'Mutated')


    @commands.command()
    async def color(self, ctx):
        await self.col(ctx)


    @commands.command()
    async def colour(self, ctx):
        await self.col(ctx)


    @commands.command()
    async def cooldown(self, ctx):
        if not ctx.guild:
            return

        member = ctx.author
        locks = CACHE[member.id]
        await ctx.send(content=
            f'Mutate: {str(locks.mutate.time)}, '
            f'usable={locks.mutate.elapsed(**MUTATE_COOLDOWN_TIME)}\n'
            f'Reroll: {str(locks.reroll.time)}, '
            f'usable={locks.reroll.elapsed(**REROLL_COOLDOWN_TIME)}')


    @commands.command(hidden=True)
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
