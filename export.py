"""export.py

Loads ExtractCog for scraping guild chat history.
"""

import logging
import sys

from discord.ext import commands

from cogs.extractor.cog import ExtractCog

import appconfig


def setup_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    # Setup logging to console
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(
        logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
    stdout_handler.setLevel(logging.INFO)
    logger.addHandler(stdout_handler)
    return logger


if __name__ == '__main__':
    logger = setup_logging()

    prefix = appconfig.fetch('BOT', 'COMMAND_PREFIX')
    token = appconfig.fetch('DISCORD', 'BOT_TOKEN')

    bot = commands.Bot(prefix)
    cog = ExtractCog(bot)
    bot.add_cog(cog)

    logger.info('Starting bot...')
    bot.run(token)
