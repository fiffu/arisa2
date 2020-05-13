import logging
import random
from typing import List, Tuple

from discord.ext import commands


from utils.memoized import memoized
from utils.feedback import FeedbackGetter
from . import config
from .embedfactory import make_embed
from .model import *
from .tag import Parser, ALIASES
from .texthelpers import codeblocked, make_two_cols

FEEDBACK = FeedbackGetter(config.FEEDBACK)


class DanbooruSearch(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _tagparse(self, query):
        # Extract the argstr, catch cases where user forgets doublequotes
        cands, alias_applied = Parser(query).candidates
        return cands, alias_applied

    @commands.command(hidden=True)
    async def tagparse(self, ctx, *args):
        # Extract the argstr, catch cases where user forgets doublequotes
        query = ' '.join(args)
        cands, alias_applied = await self._tagparse(query)
        msg = f'Parsing `{query}` yields:' + codeblocked('\n'.join(cands))

        if alias_applied:
            convs = '\n'.join([f'{alias} -> {actual}'
                               for alias, actual in alias_applied])
            msg += 'Applied alias conversions:' + codeblocked(convs)

        await ctx.send(content=msg)


    @commands.command(hidden=True)
    async def tagcheck(self, ctx, query: str):
        cand, alias_applied = Parser(
            query, spaces_to_underscore=True).first_candidate
        if not cand:
            await ctx.send(content='Unable to find any possible tags in your '
                                   f'query `{query}`')

        sorted_tags, floated, sunk, vetoed = await fetch_tag_matches(cand)

        alias_msg = ''
        if alias_applied:
            alias_msg = '\n'.join([f'{alias} -> {actual}'
                                   for alias, actual in alias_applied])

        tagstrs = [f"{t['name']} ({t['post_count']})" for t in sorted_tags]
        cols = codeblocked(make_two_cols(tagstrs))

        msgs = []

        candstr = (f'was converted into the tag candidate string `{cand}`, '
                   'which ') if cand != query else ''

        msgs.append(f'Your query for `{query}` {candstr}will resolve to:\n'
                    f'{cols}')

        for treatment in ['floated', 'sunk', 'vetoed']:
            treated_tags = locals()[treatment]
            if treated_tags:
                msgs.append(
                    f'\n{treatment.title()} tags: ' +
                    codeblocked(', '.join(t['name'] for t in treated_tags))
                )

        await ctx.send(content=''.join(msgs))


    @commands.command()
    async def tagalias(self, ctx):
        """Lists accepted short forms for various tags (requests accepted)"""
        msgs = []

        aliases = sorted(ALIASES.keys())
        maxlen = len(max(aliases, key=len))
        for alias in aliases:
            actual = ALIASES[alias]
            msgs.append(f'{alias:>{maxlen}} -> {actual}')

        msg = codeblocked('\n'.join(msgs))
        await ctx.send(content=msg)


    async def search(self, ctx, query, explicit_rating):
        async with ctx.typing():
            query = query.lower()
            posts, search_string = await smart_search(query, explicit_rating)
            selected: List[Tuple[dict, str]] = await select_posts(posts, 1)

            if not selected:
                msg = FEEDBACK.no_results(query=query)
                if explicit_rating is '-s':
                    msg = FEEDBACK.no_lewd_results(query=query)
                await ctx.send(content=msg)
                return

            post, url = selected[0]
            embed = make_embed(post, url, search_string)
            await ctx.send(content=None, embed=embed)


    @commands.command()
    async def dan(self, ctx, *args):
        async with ctx.typing():
            cmd, *query = ctx.message.content.split()
            if not query:
                return

            query = ' '.join(query)
            posts = dumb_search(query)
            selected: List[Tuple[dict, str]] = await select_posts(posts, 1)

            if not selected:
                await ctx.send(content=FEEDBACK.no_results(query=query))
                return

            post, url = selected[0]
            embed = make_embed(post, url, query, footer=False)
            await ctx.send(content=None, embed=embed)



    @commands.command()
    async def cute(self, ctx, *args):
        """Finds a cute picture with the given tag (spaces convert to _)
        """
        query = ' '.join(args)
        await self.search(ctx, query, 's')


    @commands.command()
    async def lewd(self, ctx, *args):
        """Finds a LEWD picture with the given tag"""
        query = ' '.join(args)
        await self.search(ctx, query, '-s')
