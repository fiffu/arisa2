import logging

from discord.ext import commands


log = logging.getLogger(__name__)


class EmojiStats(commands.Cog):
    """
    Misc commands
    """

    def __init__(self, bot):
        self.bot = bot


    def is_me(self, user):
        return self.bot.user.id == user.id


    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if self.is_me(user):
            return
        emoji_str = str(reaction.emoji)
        userid = user.id
        messageid = reaction.message.id
        await self.bump_emoji_usage(emoji_str, userid, messageid)


    async def bump_emoji_usage(self, emoji_str, userid, messageid):
        pass
