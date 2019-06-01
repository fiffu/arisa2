"""lastreleaselock.py

AsyncLastReleaseLock extends asyncio.Lock by caching the time when the lock
was last released.
The has_elapsed_since_last_release(datetime.timedelta) method checks if the
duration since the release time has exceeded the given timedelta.

Note that lock() should be called asynchronously.

Example:
    import asyncio
    from datetime import datetime
    from lastreleaselock import AsyncLastReleaseLock

    async def do_something(alock):
        alock = alock or AsyncLastReleaseLock()
        async with lock.acquire():
            do_something()
            # Implicit release, release_time is set to datetime.utcnow()

        await asyncio.sleep(3)
        if alock.elapsed(seconds=3):
            lock.acquire()
            do_something()
            # Set a defined datetime object as the release time
            await lock.release(time=datetime.utcnow())

The exact time that is cached
"""


from asyncio import Lock
from datetime import datetime, timedelta
from typing import Optional, Union

# Custom type indicator
Flag = int

NO_UPDATE: Flag = -1
"""Flag: indicates when lock is released, do not update last_release_time."""


class AsyncLastReleaseLock(Lock):
    """Extends extends asyncio.Lock by caching time of last lock release."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.last_release_time = None


    @property
    def time(self):
        return self.last_release_time


    def release(self, time: Union[None, datetime, Flag] = None):
        """Release the lock and set self.last_release_time with time param

        The argument to `time` controls how the self.last_release_time
        attribute will be updated:
            None      -- last_release_time will be set to datetime.utcnow()
            datetime  -- last_release_time will be set to the given datetime
            NO_UPDATE -- last_release_time won't be updated
        """
        super().release()

        if time is NO_UPDATE:
            return

        self.last_release_time = time or datetime.utcnow()


    def update(self, time: Union[datetime, str, None] = 'now'):
        """Updates the last_release_time without locking/releasing.

        Args:
            time: The datetime to set to; if 'now' then a datetime object
                  returned from datetime.utcnow(). Use None to clear the cached
                  time.
        """
        time = datetime.utcnow() if time is 'now' else time
        self.time = time


    def time_since_last_release(self) -> Optional[timedelta]:
        """timedelta since last release; None if lock has never been released.
        """
        if self.last_release_time is None:
            return None
        return datetime.utcnow() - self.last_release_time


    def has_elapsed_since_last_release(self, *args, **kwargs):
        """Create timedelta with given args and check if that has elapsed."""
        reltime = self.last_release_time

        if reltime is None:
            return True

        delta_since_rel = datetime.utcnow() - reltime
        delta = timedelta(*args, **kwargs)
        return delta_since_rel >= delta


    def elapsed(self, *args, **kwargs):
        return self.has_elapsed_since_last_release(*args, **kwargs)
