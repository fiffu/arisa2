"""main.py

Main app entry point.
"""

import logging
import sys

from discord.ext import commands

from cogs import ENABLED_COGS
import appconfig

DEBUGGING = appconfig.DEBUGGING


if __name__ == '__main__':
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    # Setup logging to console
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(logging.INFO)

    # Timestamp already available on Heroku logstream
    timestamp = '%(asctime)s:' if DEBUGGING else ''
    log_format = timestamp + '%(levelname)s:%(name)s: %(message)s'
    stdout_handler.setFormatter(logging.Formatter(log_format))

    logger.addHandler(stdout_handler)

    prefix = appconfig.fetch('BOT', 'COMMAND_PREFIX')

    if DEBUGGING:
        logger.warning('Starting in debug mode.')

    bot = commands.Bot(prefix)

    num_cogs_loaded = 0
    for cog_cls in ENABLED_COGS:
        try:
            cog = cog_cls(bot)  # instantiate cog class
            bot.add_cog(cog)
            num_cogs_loaded += 1
            # logger.info('Registered cog %s', cog.qualified_name)

        except commands.CommandError as e:
            logger.error('Failed to load cog: %s.%s',
                         cog.__module__, cog.__name__)

    logger.info('Total of %s cogs loaded', num_cogs_loaded)

    token = appconfig.fetch('DISCORD', 'BOT_TOKEN')

    logger.info('Starting bot...')
    bot.run(token)
