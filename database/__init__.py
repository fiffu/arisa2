import asyncio
import logging

import aiopg

import appconfig


log = logging.getLogger(__name__)


URL = appconfig.fetch('DATABASE', 'URL')

DEFAULT_POOL_ARGS = {
    'dsn': URL,
}

POOL = None


class PoolClosedError(RuntimeError):
    pass


async def setup_pool(**kwargs):
    global POOL  # module-level only; not "true" global scope


    try:
        if POOL and POOL.closed:
            msg = 'Cannot setup already-closed connection pool'
            log.exception(msg)
            raise PoolClosedError(msg)

        if not POOL:
            kw = DEFAULT_POOL_ARGS.copy()
            kw.update(kwargs)
            POOL = await aiopg.create_pool(**kw)
            log.info('Database connection initialized.')

    except Exception as e:
        log.error('Failed to setup database connection pool: %s', e)
        log.exception(e)
        raise e


def get_pool(loop=None):
    global POOL

    try:
        if not POOL:
            sync_setup_pool(loop)

        if POOL.closed:
            msg = 'attempted to acquire from closed connection pool'
            log.error(msg)
            raise PoolClosedError(msg)

    except Exception as e:
        log.exception(e)
        raise e

    return POOL


def sync_setup_pool(loop=None):
    loop = loop or asyncio.get_event_loop()
    loop.run_until_complete(setup_pool())


def close_pool():
    global POOL

    if POOL.closed:
        return

    # Signal connections to close
    POOL.close()
    log.info('Shutting down database connection pool.')


sync_setup_pool()
