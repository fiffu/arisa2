"""anypartial.py

anypartial()
    Allows you to regular functions as well as coroutine functions (defined
    either with `yield` or `async def`).
"""


from functools import partial
import inspect

def anypartial(func, *args, **kwargs):
    """Partialling that works for both sync and async functions"""
    if inspect.iscoroutinefunction(func):
        async def wrapper(*extra_args, **extra_kwargs):
            return await func(*args, *extra_args, **kwargs, **extra_kwargs)
    else:
        wrapper = partial(func, *args, **kwargs)
        wrapper.__module__ = func.__module__
        wrapper.__name__ = func.__name__
    return wrapper
