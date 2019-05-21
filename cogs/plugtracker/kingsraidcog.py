# -*- coding: utf-8 -*-

from typing import Mapping, Sequence

from discord.ext import commands

from cogs.tracking.trackercog import TrackerCog

from .plugmixin import PlugMixin, PlugPost
from .embedfactory import new_plug_embed


URLS = {
    '[★Notice★]':
        'https://www.plug.game/kingsraid/1030449/posts?menuId=1',
    '[★Patch Note★]':
        'https://www.plug.game/kingsraid/1030449/posts?menuId=9',
    '[★Game Content★]':
        'https://www.plug.game/kingsraid/1030449/posts?menuId=32',
    # 'Central Orvel (Events)': 
        # 'https://www.plug.game/kingsraid/1030449/posts?menuId=2',
    # 'Green Note':
    #     'https://www.plug.game/kingsraid/1030449/posts?menuId=12',
    # 'Challenge Raid':
    #     'https://www.plug.game/kingsraid/1030449/posts?menuId=14',
    # 'Talk to GM Orvel':
    #     'https://www.plug.game/kingsraid/1030449/posts?menuId=19',
    # 'GM Note':
    #     'https://www.plug.game/kingsraid/1030449/posts?menuId=22',
    # "King's VOD":
    #     'https://www.plug.game/kingsraid/1030449/posts?menuId=24',
}


class PlugKingsRaidCog(PlugMixin, TrackerCog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.new_posts = []

    @property
    def plug_forum_name_urls(self) -> Mapping[str, str]:
        """Mapping[forumName, forumUrl]"""
        return URLS


    async def handle_new_posts(self, new_posts: Sequence[PlugPost]) -> None:
        self.new_posts = new_posts


    @commands.command()
    async def latest(self, ctx):
        if self.new_posts:
            last = sorted(self.new_posts, key=lambda p: p.timestamp)[0]
            embed = new_plug_embed(last)
            await ctx.send(content=None, embed=embed)
