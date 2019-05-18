import async_timeout
import aiohttp
import asyncio

FETCH_TIMEOUT_SECS = 10


async def pull_pages(loop, urls, **kwargs):
    async with aiohttp.ClientSession() as aiosess:
        results = await asyncio.gather(
            *[aiosess.get(url, **kwargs) for url in urls], 
            loop=loop,
            return_exceptions=True
        )
    
    return zip(urls, results)

