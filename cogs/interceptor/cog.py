import logging
import re

from discord import Embed
from discord.ext import commands

from .scrapers import pixiv

class Interceptor(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    @commands.Cog.listener()
    async def on_message(self, message):
        atts = message.attachments
        if not atts:
            return

        for att in atts:
            if not att.filename:
                continue

            pixiv_match = re.match(r"""(\d+)_p\d+_(master\d+)\.\w+""",
                                   att.filename)
            if pixiv_match:
                pic_id, size = pixiv_match.groups()
                # url = pixiv(pic_id)
                # The scraper works but can't hotlink to the pic
                url = f'https://www.pixiv.net/en/artworks/{pic_id}'
                desc = f'>{size}\nSauce on Pixiv: [{pic_id}]({url})'
                embed = Embed(description=desc)
                # embed.set_image(url=url)
                await message.channel.send(embed=embed)
                # await message.channel.send(content=repr(url))
                return
