from collections import defaultdict
from typing import Any, Callable


class keydefaultdict(defaultdict):
    def __init__(self, factory: Callable[[str], Any]):
        super().__init__(None)  # No default_factory for underlying defaultdict
        self.factory = factory


    def __missing__(self, key):
        # Rebind so it looks like function call, not method call
        factory = self.factory

        # Call factory on key
        val = factory(key)

        # Assign the return value
        self[key] = val

        return val
