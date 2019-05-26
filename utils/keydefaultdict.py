"""keydefaultdict.py

The keydefaultdict class extends collections.defaultdict by passing the
missing key to the callable that was provided to the default_factory
parameter during instantiation.

Example:
    # Possible usecase: memoization

    import uuid
    from keydefaultdict import keydefaultdict

    class Employee:
        def __init__(self, name):
            self.name = name
            self.uuid = uuid.uuid4()  # random uuid

    kdd = keydefaultdict(lambda key: Employee(key))

    uuids = []
    for name in ['alice', 'bob']:
        emp = kdd['john']
        uuids.append(emp.uuid)


"""

from collections import defaultdict
from typing import Any, Callable


class keydefaultdict(defaultdict):
    """defaultdict that passes the missing key to default_factory callable."""
    def __init__(self, factory: Callable[[str], Any]):
        # Init base defaultdict without default_factory
        super().__init__(None)
        self.factory = factory


    def __missing__(self, key):
        # Rebind so it looks like function call, not method call
        factory = self.factory

        # Call factory on key
        val = factory(key)

        # Assign the return value
        self[key] = val

        return val
