from datetime import datetime, timedelta
import inspect


CACHE_RESULT_EXPIRY = timedelta(days=1)


class memoized(object):
    """Decorator for caching function calls.

    Adapted from SO answer by georg: https://stackoverflow.com/a/10921408
    """
    def __init__(self, func):
       self.func = func
       self.cache = dict()
       self.expiry = CACHE_RESULT_EXPIRY

    def __call__(self, *args, **kwargs):
        key = self.make_key(args, kwargs)
        time_now = datetime.now()
        if not self.have_cached(key, time_now):
            self.cache[key] = dict()
            self.cache[key]['result'] = self.func(*args, **kwargs)
            self.cache[key]['time'] = time_now
        return self.cache[key]['result']

    def have_cached(self, key, time_now):
        try:
            time_since_cached = time_now - self.cache[key]['time']
            return time_since_cached < CACHE_RESULT_EXPIRY
        except KeyError:
            return False

    def normalize_args(self, args, kwargs):
        spec = inspect.getargs(self.func.__code__).args
        return dict(
            list(kwargs.items()) + list(zip(spec, args))
        )

    def make_key(self, args, kwargs):
        # Args should always normalized
        a = self.normalize_args(args, kwargs)
        # The return value provides the key that identifies the cached result
        return tuple(sorted(a.items()))