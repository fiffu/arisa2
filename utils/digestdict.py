# Bind to module scope
abs_, len_, min_, max_ = abs, len, min, max

def lev(a, b, tolerance=2, sentinel=1000):
    i, j = len_(a), len_(b)

    # Upper bound is length diff, quit if length difference is too big
    if abs_(i - j) > tolerance:
        return sentinel

    # Quit early if we know the minimum number of substitutions to make will
    # already be too big
    diff = len_({*a}.symmetric_difference({*b})) // 2
    if diff > tolerance:
        return sentinel

    # Special case where one of the strings is length 0
    if not (i * j):
        return max_(i, j)

    A, B = a[:-1], b[:-1]
    return min_(
        lev(A, b) + 1,
        lev(a, B) + 1,
        lev(A, B) + (a[-1] != b[-1])
    )


def autocorrect(query, candidates, tolerance=2):
    cands = [(lev(query, c, tolerance), c) for c in candidates]
    return [cand for n, cand in sorted(cands) if n <= tolerance]



class DigestDict:
    """A dictionary-like class that can be indexed using "digested" keys

    The digest() method creates alias ("digested") keys from the original
    ("main") keys added to the dictionary.

    Keys are digested whenever the dictionary is populated in the usual ways
    (using update() or fromkeys() etc). For finer control -- such as stopping
    keys from being digested, or providing extra aliases -- is available
    using the add() method.

    Indexing the dictionary or using the fetch() method will lookup among
    digested as well as main keys. The get() and dictionary view methods
    will lookup among main keys.

    Deleting or popping items in the dictionary will delete its corresponding
    digested keys as well.
    """

    def __init__(self, **kwargs):
        self._dic = {}  # main key-value store
        self._digested = {}  # maps digested keys to key in main dict
        #self._cached = {}  # cache lookups for next time we see the same query

        # Implement the pythonic kwargs-construction
        self.update(kwargs)


    def add(self, key, value, predigested=None, digest=True):
        """Inserts a key-value pair, while generating the digested key(s)

        Arguments:
        predigested - list of aliases to store among this key's digested keys
        digest - controls whether key should be additionally digested with
                 self.digest()
        """
        digested = []
        if predigested:
            digested.extend(predigested)

        if digest:
            _, d = self.digest(key)
            digested.extend(d)

        for d in digested:
            assert d not in self._digested, f'duplicated digested key: {d}'
            self._digested[d] = key

        self._dic[key] = value
        return [key] + [digested]


    def digest(self, key):
        """The default method to digest a key with

        This method should return (str, list)
        """
        if len(key) == 0:
            return '', ''

        *heads, tail = key.split()
        prefix = ''.join(word[0] for word in heads)

        digested = []
        if prefix:
            digested.append(prefix + tail)
        return key, digested


    def digesteditems(self, sort=True):
        """Generates key-value pairs from the digested dict

        Arguments:
        sort - Whether the keys from the main dict should be yielded before
               the digested keys, in alphabetical sort order
        """
        if not sort:
            yield from self._digested.items()

        else:
            keys = sorted(list(self._digested.keys()), key=str.lower)
            for k in keys:
                yield k, self._digested[k]


    def fetch(self, key, default=None, autocomplete=True):
        """Similar to dict.get() but checks the digested keys too

        Key lookups will check in the main dictionary keys before checking
        digested keys. Autocomplete, if used, will try to resolve the given
        key to a full-length main or digested key.
        Autocomplete may be slow, so it is optional if lookup takes too long.

        Arguments:
        default - Value to return if lookup fails
        autocomplete - Whether autocomplete should be used
        """
        if key in self._dic:
            return self._dic[key]

        elif key in self._digested:
            return self._dic[self._digested[key]]

        elif autocomplete:
            cand = self.candidates(key, limit=1)
            if not cand:
                return default
            cand = cand[0]
            return (
                self._dic.get(cand)
                or self._dic.get(self._digested[cand])
                or default
            )

        else:
            return default


    def candidates(self, partialkey, limit=10):
        """Returns a list of autocomplete candidates for a given key"""
        def search(items, results, limit):
            keys = [k for k, v in sorted(items, key=lambda x: len(x[0]))]
            for k in keys:
                if len(results) == limit:
                    break
                if k.startswith(partialkey):
                    results.append(k)

        out = []
        search(self._dic.items(), out, limit)

        dig_items = list(self.digesteditems())
        search(dig_items, out, limit)

        if len(out) < limit:
            keys = [k for k, v in dig_items] + list(self._dic.keys())
            cands = autocorrect(partialkey, keys)
            out.extend(cands)
            out = out[:limit]

        return out


    def aliases(self, key):
        return [dig
                for dig, actual in self._digested.items()
                if actual == key]


    """
    Removing items
    """
    def __delitem__(self, key):
        val = self._dic[key]
        aliases = self.aliases(key)
        try:
            for alias in aliases:
                del self._digested[alias]
            del self._dic[key]
            return val

        except BaseException:
            # Catch, undo delete, raise
            for alias in aliases:
                self._digested[alias] = key
                self._dic = val
            raise

    def pop(self, key):
        return self.__delitem__(key)

    def popitem(self):
        keys = list(self._dic.keys())
        if not keys:
            {}.popitem()  # No keys; reuse 'dictionary is empty' KeyError
        key = keys[-1]
        return key, self.pop(key)


    """
    Emulate dictionary interface
    """
    @classmethod
    def fromkeys(cls, seq, val):
        new = cls()
        for key in seq:
            new.add(key, val)
        return new

    def update(self, dictionary):
        for k, v in dictionary.items():
            self.add(k, v)

    def copy(self):
        new = self.__class__()
        new._dic = self._dic.copy()
        new._digested = self._digested.copy()
        return new

    """
    Python magic methods
    """
    def __setitem__(self, key, val):
        self.add(key, val)

    def __getitem__(self, key):
        return self.fetch(key)

    def __repr__(self):
        return 'DigestDict(%s)' % self._dic.__repr__()

    """
    Do the remaining read-only methods using self._dic
    Includes get() and view methods like keys(), values(), items() etc
    """
    def __getattr__(self, attr):
        """Handles .get(), .fromkeys() etc"""
        return getattr(self._dic, attr)
