"""memoized.py

@memoized is a decorator that memoizes the return value of a function or
method call.
"""

from datetime import datetime, timedelta
import inspect
from typing import Any, Callable, Optional, Tuple


CACHE_RESULT_EXPIRY = timedelta(days=1)
"""timedelta: Time before cached results are considered to have expired.

Expired cached results will not returned, so the wrapped function/method will
be invoked to obtain new results.
Warning: Expired results are not automatically garbage-collected.

TODO:
    - Add a gc() garbage-collection method that deletes expired cached results
"""


class memoized(object):
    """Decorator for caching function calls.

    Adapted from SO answer by georg: https://stackoverflow.com/a/10921408
    """
    def __init__(self, func: Callable):
        self.func = func
        self.cache = dict()
        self.expiry = CACHE_RESULT_EXPIRY


    def __call__(self, *args, **kwargs):
        """Invokes wrapped function and caches its result"""
        key = self.make_key(args, kwargs)
        time_now = datetime.now()
        if not self.have_cached(key, time_now):
            self.cache[key] = dict()
            self.cache[key]['result'] = self.func(*args, **kwargs)
            self.cache[key]['time'] = time_now
        return self.cache[key]['result']


    def have_cached(self,
                    key: tuple,
                    time_now: Optional[datetime] = None) -> bool:
        """Checks for a cached, non-expired result"""
        try:
            time_now = time_now or datetime.now()
            time_since_cached = time_now - self.cache[key]['time']
            return time_since_cached < CACHE_RESULT_EXPIRY
        except KeyError:
            return False


    def normalize_args(self, args, kwargs):
        """Packs args and kwargs into a unified dict representation"""
        spec = inspect.getargs(self.func.__code__).args
        return dict(
            list(kwargs.items()) + list(zip(spec, args))
        )


    def make_key(self,
                 args: tuple,
                 kwargs: dict) -> Tuple[Tuple[str, Any], ...]:
        """Creates tuple of sorted (key,val) from args and kwargs"""
        # Args should always normalized
        a = self.normalize_args(args, kwargs)
        # The return value provides the key that identifies the cached result
        return tuple(sorted(a.items()))
