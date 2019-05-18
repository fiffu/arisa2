import logging

from utils import mash, SoftDict
from .updater import read_files, update_dataset


log = logging.getLogger(__name__)


KR_CACHE = SoftDict()


class KREntity:
    __slots__ = """
        data eng
        index class position type auto mpatk mpsec
        name subtitle description s1 s2 s3 s4 t5 uw
        story
        iconurl portraiturl mogurl
        entity
    """.split()

    from_data = 'index class position type auto mpsec mpatk'.split()
    from_eng = 'name subtitle description s1 s2 s3 s4 t5 uw story'.split()

    def __init__(self, index, eng, data, entity):
        assert entity, 'entity argument cannot be falsey'
        self.eng = eng
        self.data = data or dict()
        self.entity = entity
        self.index = int(index)

        N = self.name
        self.mogurl = "https://maskofgoblin.com/{}/{}".format(
            entity.lower(), self.index)
        if entity is 'Hero':
            self.iconurl = f"http://krw-img-thumb.s3.amazonaws.com/{N}ico.png/70px-{N}ico.png"
            self.portraiturl = f"http://krw-img.s3.amazonaws.com/{N}5star.png"


    @property
    def mash(self):
        return mash(self.name)


    def memo(self, name, value):
        setattr(self, name, value)
        return value


    def merge(self, text, data):
        """Formats text with data, recursively if needed

        Raises ValueError if text and data are not compatible datatypes."""
        # Text needs no formatting
        if not data:
            return text

        # Return formatted text
        elif getattr(text, 'format', None):
            return text.format(*data)

        # Walk dict
        elif getattr(text, 'items', None):
            for k, v in text.items():
                if k == 'books':
                    # Coerce the dict at text['books'] into a list
                    v = [y for (x, y) in v.items()]
                if k == 'linked':
                    # Convert the list at data['linked'] into a dict
                    data[k] = {'description': data[k]}
                text[k] = self.merge(v, data.get(k, None))
            return text

        # Walk list
        elif getattr(text, 'sort', None):
            for i, x in enumerate(text):
                new = None
                try:
                    new = data[i]
                except IndexError:
                    pass
                text[i] = self.merge(x, new)
            return text

        else:
            t = str(type(text))
            d = str(type(data))
            msg = (f"data structures of 'text' ({t}) and 'data' ({d}) are "
                    "not compatible")
            raise ValueError(msg)


    def get_eng(self, attr):
        text = self.eng[attr]
        data = self.data.get(attr, None)

        newtext = self.merge(text, data)
        return self.memo(attr, newtext)


    def get_data(self, attr):
        if attr == 'auto':
            times = []
            for grp in self.data['auto']['time']:
                if len(grp) == 1:
                    times.append(str(grp[0]))
                else:
                    j = ' '.join(map(str, grp))
                    times.append(j)
            self.data['auto']['clusters'] = ' / '.join(times)

        return self.memo(attr, self.data[attr])


    def items(self):
        attrs = filter(lambda a: getattr(self, a, None), self.__slots__)
        for attr in attrs:
            yield attr, getattr(self, attr)


    def __getattr__(self, name):
        try:
            if name in self.from_data:
                return self.get_data(name)
            elif name in self.from_eng:
                return self.get_eng(name)
            else:
                raise AssertionError
        except (KeyError, AssertionError):
            msg = f"'{self.entity}' object has no attribute '{name}'"
            raise AttributeError(msg)


    def __repr__(self):
        return f'<KR {self.entity}: {self.name}>'


class Hero(KREntity):
    def __init__(self, *args, **kwargs):
        super(Hero, self).__init__(*args, **kwargs, entity='Hero')


class Artifact(KREntity):
    def __init__(self, *args, **kwargs):
        super(Artifact, self).__init__(*args, **kwargs, entity='Artifact')


def load_heroes_artifacts():
    data, eng = read_files()

    heroes, artifacts = [], []

    for entity, li in [
        ('Hero', heroes),
        ('Artifact', artifacts)
    ]:
        jsonkey = entity.lower()

        for index, english in eng[jsonkey].items():
            fmtargs = None if entity == 'Artifact' else data[jsonkey][index]
            obj = KREntity(index, english, fmtargs, entity)
            if obj.name == 'Lilia':
                obj.iconurl = 'https://maskofgoblin.com/img/hero.a5b9bbe7.png'
            li.append(obj)

    return heroes, artifacts


def build_kr_cache():
    """Caches db into app memory"""
    log.info('Building KR cache...')
    ha = [*load_heroes_artifacts()]
    for entities in ha:
        for e in entities:
            KR_CACHE[e.name] = e
            KR_CACHE.memo['lolias'] = 'Lilia'
            KR_CACHE.memo['Lolias'] = 'Lilia'
    h, a = ha
    log.info(f'KR database cache built - {len(h)} heroes, {len(a)} artifacts')


def search(search_name):
    cache = get_cache()
    return cache.get(search_name, None)


def get_cache(entity=''):
    """Use this to access the cache and search for heroes and artifacts"""
    if not KR_CACHE:
        build_kr_cache()
    if entity in ['Hero', 'Artifact']:
        return {x: y for x, y in KR_CACHE.items() if y.entity == entity}
    return KR_CACHE


async def update(loop):
    log.info("Starting King's Raid database update...")
    await update_dataset(loop)
    build_kr_cache()


def heroes():
    return get_cache('Hero')


def artifacts():
    return get_cache('Artifact')
