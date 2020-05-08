import asyncio
import logging
from threading import Lock as ThreadingLock

import aiopg

import appconfig


log = logging.getLogger(__name__)


URL = appconfig.fetch('DATABASE', 'URL')

DEFAULT_POOL_ARGS = {
    'dsn': URL,
}

POOL = None
CLOSING = False

LOCK = asyncio.Lock()
LOCK_SYNC = ThreadingLock()

class PoolClosedError(RuntimeError):
    pass


async def setup_pool(**kwargs):
    global CLOSING, LOCK, POOL

    async with LOCK:
        try:
            if POOL and POOL.closed:
                msg = 'Cannot setup already-closed connection pool'
                log.exception(msg)
                raise PoolClosedError(msg)

            if not POOL:
                kw = DEFAULT_POOL_ARGS.copy()
                kw.update(kwargs)
                POOL = await aiopg.create_pool(**kw)
                CLOSING = False
                log.info('Database connection pool ready.')

        except BaseException as e:
            log.error('Failed to setup database connection pool: %s', e)
            log.exception(e)
            raise e


async def get_pool():
    global POOL

    try:
        if not POOL:
            await setup_pool()

        if POOL.closed:
            msg = 'attempted to acquire from closed connection pool'
            log.error(msg)
            raise PoolClosedError(msg)

    except Exception as e:
        log.exception(e)
        raise e

    return POOL


# def sync_setup_pool(loop=None):
#     loop = loop or asyncio.get_event_loop()
#     fut = loop.call_soon(setup_pool)
#     try:
#         timeout = 5
#         fut.result(timeout)
#     except asyncio.TimeoutError:
#         fut.cancel()
#         log.error('Timed out while waiting to set up connection')


def close_pool(loop=None):
    global POOL, CLOSING, LOCK_SYNC

    with LOCK_SYNC:

        if CLOSING or POOL.closed:
            return

        # Signal connections to close
        POOL.close()
        CLOSING = True

        log.info('Closing database connection pool.')
        coro = POOL.wait_closed()
        loop = loop or asyncio.get_event_loop()
        loop.run_until_complete(coro)
        log.info('Database connection pool shut down.')
        # try:
        #     yield from future
        # except asyncio.TimeoutError:
        #     print('Shutdown took too long, returning control without cancel...')
        # else:
