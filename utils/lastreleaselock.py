from asyncio import Lock
from datetime import datetime, timedelta
from typing import Union

NO_UPDATE = -1


class AsyncLastReleaseLock(Lock):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.last_release_time = None


    @property
    def time(self):
        return self.last_release_time


    def release(self, time: Union[None, datetime, int] = None):
        """Release the lock and set self.last_release_time with time param

        The argument to `time` controls how the self.last_release_time
        attribute will be updated:
            None      -- attribute will be set to datetime.now()
            datetime  -- attribute will be set to the given datetime object
            NO_UPDATE -- attribute won't be updated
        """
        super().release()

        if time is NO_UPDATE:
            return

        self.last_release_time = time or datetime.now()


    def update(self, time='now'):
        time = datetime.now() if time is 'now' else time
        self.time = time


    def time_since_last_release(self):
        if self.last_release_time is None:
            return None
        return datetime.now() - self.last_release_time


    def has_elapsed_since_last_release(self, *args, **kwargs):
        reltime = self.last_release_time

        if reltime is None:
            return True

        delta_since_rel = datetime.now() - reltime
        delta = timedelta(*args, **kwargs)
        return delta_since_rel >= delta


    def elapsed(self, *args, **kwargs):
        return self.has_elapsed_since_last_release(*args, **kwargs)
