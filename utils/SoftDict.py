"""softdict.py

SoftDict extends dict by supporting "soft indexing", which allows looking up
keys using their substrings or initials.
The keys used in a SoftDict must support string methods.
"""

from typing import Optional

from utils import mash


class SoftDict(dict):
    """Dict supporting "soft indexing" by initials and partial key matches."""
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.initials = dict()
        self.mashed = dict()
        self.memo = dict()


    def __setitem__(self, key, val):
        if not getattr(key, 'split', None):
            raise TypeError("keys must be string-like objects which support "
                            "the split() method.")
        m = mash(key)
        self.mashed[m] = key

        ws = key.split()
        i = ''.join(w[0] for w in ws) if len(ws) > 2 else None
        if i:
            self.initials[i] = key
        super().__setitem__(key, val)


    def __delitem__(self, key):
        for a in ['mashed', 'initials']:
            att = getattr(self, a)
            for alias, actualname in att.items():
                if actualname == key:
                    del att[alias]
                    break
        super().__delitem__(key)


    def __missing__(self, searching):
        """Called when indexing SoftDict[key] if key is not in SoftDict."""
        # Check against case-sen initials, then mash, then case-insen initials

        # Return result from memoized orig_key, if any
        orig_key = self.find_key("memo", searching, exact=True)
        if orig_key:
            return super().__getitem__(orig_key)

        # Case-sensitive searches first
        if not searching.islower():
            # Exact name match
            for key in super().__iter__():
                if key.startswith(searching):
                    orig_key = key
            # Check against initials
            orig_key = self.find_key("initials", searching)

        # Memoize and return here if matching actual key is found
        if orig_key:
            self.memo[searching] = orig_key
            return super().__getitem__(orig_key)

        # Case-insensitive searches
        m = mash(searching)

        for attr in ['mashed', 'initials']:
            args = (attr, m, True)
            # Following stmt short-circuits if exact lowercase match is found
            orig_key = (
                self.find_key(*args, True)  # alias == m
                or self.find_key(*args, False)  # alias.startswith(m)
                or self.find_key(*args, False, True)  # m in alias
            )
            # Stop asap if match is found
            if orig_key:
                break

        # Memo and return if orig_key found, else complain
        if orig_key:
            self.memo[searching] = orig_key
            return super().__getitem__(orig_key)

        raise KeyError(searching)


    def find_key(self,
                 attr: str,
                 k: str,
                 lower: bool = False,
                 exact: bool = False,
                 substring: bool = False) -> Optional[str]:
        """Attempts to find a existing key that matches the input string.

        Args:
            attr: Either 'mashed' or 'initials'. If 'mashed', checks against
                  mashed strings (lowercase strings with non-alnum characters
                  removed)
            k: The input string that we want to match to some existing key
            lower: Check against unmashed actual keys set to lowercase
            substring: Check against substrings of unmashed actual keys
        """
        dattr = getattr(self, attr)
        for alias in sorted(dattr.keys()):
            actual = dattr[alias]
            if lower:
                alias = alias.lower()
            if exact:
                if k == alias:
                    return actual
            else:
                if alias.startswith(k):
                    return actual
                if substring and (k in alias):
                    return actual

        return None


    def get(self, key, default=None):
        """The inherited `get` doesn't trigger __missing__."""
        try:
            return self[key]
        except KeyError:
            return default
