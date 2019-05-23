import logging
import random 
from typing import List, Tuple

#from bs4 import BeautifulSoup
from discord.ext import commands
#import requests

from . import config
from .client import CLIENT
from .tag import Parser, ALIASES
from .texthelpers import codeblocked, make_two_cols


log = logging.getLogger(__name__)

client = CLIENT


def process_tags(taglist) -> Tuple[List, List, List, List]:
    taglist = sorted(taglist, key=lambda t: t['post_count'], reverse=True)

    veto = config.VETO
    floats = config.FLOATS
    sinks = config.SINKS
    
    floated, regular, sunk, vetoed = [], [], [], []
    for tag in taglist:
        name = tag['name']
        
        if name in veto:
            vetoed.append(tag)
            log.info(f'Discarding vetoed tag "{name}"')
            continue

        for x in sinks:
            if x in name:
                sunk.append(tag)
                break
        else:
            # For-else means proceed here if tag was not sunken
            for x in floats:
                if x in name:
                    floated.append(tag)
                    break
            else:
                regular.append(tag)

    sorted_tags = floated + regular + sunk
    return sorted_tags, floated, sunk, vetoed


async def fetch_tag_matches(candidate):
    if not candidate.endswith('*'):
            candidate += '*'

    taglist = client.tag_list(candidate)
    return process_tags(taglist)


class DanbooruCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def tagparse(self, ctx, query: str):
        # Extract the argstr, catch cases where user forgets doublequotes
        _, *argstr = ctx.message.content.split(None, 1)
        argstr = argstr[0] if argstr else ''
        if len(argstr) > len(query):
            query = argstr
        
        cands, alias_applied = Parser(query).candidates
        msg = f'Parsing `{query}` yields:' + codeblocked('\n'.join(cands))
        
        if alias_applied:
            convs = '\n'.join([f'{alias} -> {actual}'
                               for alias, actual in alias_applied])
            msg += 'Applied alias conversions:' + codeblocked(convs)

        await ctx.send(content=msg)


    @commands.command()
    async def tagcheck(self, ctx, query: str):
        cand, alias_applied = Parser(
            query, spaces_to_underscore=True).first_candidate
        if not cand:
            await ctx.send(content='Unable to find any possible tags in your '
                                   f'query `{query}`')

        await ctx.trigger_typing()
        sorted_tags, floated, sunk, vetoed = await fetch_tag_matches(cand)
        
        alias_msg = ''
        if alias_applied:
            alias_msg = '\n'.join([f'{alias} -> {actual}' 
                                   for alias, actual in alias_applied])
        
        tagstrs = [f"{t['name']} ({t['post_count']})" for t in sorted_tags]
        cols = codeblocked(make_two_cols(tagstrs))

        msgs = []

        candstr = (f'was converted into the tag candidate string {cand}, '
                   'which ') if cand != query else ''
        
        msgs.append(f'Your query `{query}` {candstr}will resolve to:\n{cols}')

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
        msgs = []
        
        aliases = sorted(ALIASES.keys())
        maxlen = len(max(aliases, key=len))
        for alias in aliases:
            actual = ALIASES[alias]
            msgs.append(f'{alias:>{maxlen}} -> {actual}')
        
        msg = codeblocked('\n'.join(msgs))
        await ctx.send(content=msg)