import logging
import sys

import discord
from discord.ext import commands

from cogs import ENABLED_COGS
import appconfig

DEBUGGING = appconfig.DEBUGGING

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# Setup logging to console
stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setFormatter(
    logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
stdout_handler.setLevel(logging.INFO)
logger.addHandler(stdout_handler)

prefix = appconfig.fetch('BOT', 'COMMAND_PREFIX')


if __name__ == '__main__':
    if DEBUGGING:
        logger.warning('Starting in debug mode.')
    
    bot = commands.Bot(prefix)

    num_cogs_loaded = 0
    for cog_cls in ENABLED_COGS:
        try:
            cog = cog_cls(bot)  # instantiate cog class
            bot.add_cog(cog)
            num_cogs_loaded += 1
            logger.info('Registered cog ' + cog.qualified_name)
        
        except commands.CommandError as e:
            logger.error('Failed to load cog: {}.{}'.format(
                           cog.__module__, cog.__name__))

    logger.info(f'Total of {num_cogs_loaded} cogs loaded')
    
    token = appconfig.fetch('DISCORD', 'BOT_TOKEN')
    
    logger.info(f'Starting bot...')
    bot.run(token)
