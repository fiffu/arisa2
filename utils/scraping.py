"""scraping.py

Simple function to pull webpages by bulk.
"""

import asyncio
from typing import List, Union, Tuple

import aiohttp


FETCH_TIMEOUT_SECS = 10
""""""

# Type aliases
Url = str
Result = Union[aiohttp.ClientResponse, Exception]


async def pull_pages(loop: asyncio.AbstractEventLoop,
                     urls: List[Url],
                     **kwargs) -> List[Tuple[Url, Result]]:
    """Pulls the given URLs by bulk. Returns when all complete.

    Args:
        loop: the asyncio.Loop to use
        urls: list of URLs to pull
        kwargs: keyword args to pass to aiohttp.ClientSession.get()
    """
    async with aiohttp.ClientSession() as aiosess:
        # Results are ordered according to the order in `coros`
        coros = [aiosess.get(url, **kwargs) for url in urls]
        results = await asyncio.gather(
            *coros,
            loop=loop,
            return_exceptions=True
        )

    return zip(urls, results)
