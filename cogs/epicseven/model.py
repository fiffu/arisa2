from collections import defaultdict
import itertools
import json
import re
import warnings

import requests

from utils import DigestDict


SRC = 'lab.json'
# JSON data gratefully obtained from epicseventools.com


SPEC_CHANGE = {
    'lorina': 'commander lorina',
    'montmorancy': 'angelic montmorancy',
    'hazel': 'mascot hazel',
    'carrot': 'researcher carrot',
    'kluri': 'falconer kluri',
    'roozid': 'righteous thief roozid',
    'butcher corps inquisitor': 'chaos sect inquisitor',
    'church of ilryos axe': 'chaos sect axe',
}


class Constraint:
    keys = 'any,defbreak,knight,mage,ranger,soul weaver,thief,warrior'
    flagsdict = DigestDict()
    for key in keys.split(','):
        flagsdict[key] = key

    @classmethod
    def read(cls, arg):
        return cls.flagsdict[arg]

    def __getattr__(self, attr):
        val = self.flagsdict[attr]
        if not val:
            cls = self.__class__.__name__
            raise AttributeError(f"object '{cls}' has no attribute 'attr'")
        return val
Constraint = Constraint()


HEROES = None
BEST_CHAT_YIELD_CACHE = dict()  # Map[str: List[Tuple[str, int]]]

# def load():
#     global HEROES
#     with open(CSV, 'r', encoding='utf-8') as f:
#         lines = f.readlines()

#     # Discard rows until we reach the header
#     while not lines[0].startswith('Chat1,Chat2,Hero'):
#         lines = lines[1:]
#     header, *rows = lines

#     _, _, _, *chatoptions, _ = header.split(',')

#     heroes = DigestDict()
#     for row in rows:
#         chat1, chat2, heroname, *chatvalues, average = row.split(',')
#         try:
#             assert chat1 in chatoptions, 'invalid chat option ' + repr(chat1)
#             assert chat2 in chatoptions, 'invalid chat option ' + repr(chat2)
#             assert len(chatvalues) == len(chatoptions)
#         except AssertionError as e:
#             warnings.warn(f'Failed to load {heroname} ({e})')
#             continue

#         name = ' '.join(re.findall('[A-Z][a-z]+', heroname)).lower()
#         hero = dict(
#             name=name,
#             chat1=chat1,
#             chat2=chat2,
#         )
#         hero.update({k: int(v) for k, v in zip(chatoptions, chatvalues)})
#         heroes[name] = hero

#     HEROES = heroes
#     return heroes

def load_json(file):
    with open(file) as f:
        return json.load(f)


def pluckfrom(iterable):
    for i, item in enumerate(iterable):
        yield item, iterable[0:i] + iterable[i + 1:]


def load():
    global HEROES

    jsondata = load_json(SRC)

    heroes = DigestDict()
    for hero in jsondata:
        try:
            hero.update(hero['Reactions'])
            name = hero['Name'].lower()
            hero['Class'] = hero['Class'].replace('-', ' ')  # for soul-weaver
            heroes.add(name, hero)

        except BaseException as e:
            warnings.warn(f'Failed to parse {hero} ({e})')
            continue

    HEROES = heroes
    return heroes


def best_candidates_for_option(chatoption, pool=None):
    """
    (chatoption: str, pool: dict) -> list(tuple(gain: int, heroname: str))
    """
    if pool:
        gains = [(v[chatoption], k) for k, v in pool.items()]
        return gains

    if chatoption not in BEST_CHAT_YIELD_CACHE:
        gains = [(v[chatoption], k) for k, v in HEROES.items()]
        BEST_CHAT_YIELD_CACHE[chatoption] = sorted(gains, reverse=True)

    return BEST_CHAT_YIELD_CACHE[chatoption]


def calculate_morale(hero1, hero2, hero3, hero4):
    global HEROES
    if HEROES is None:
        HEROES = load()

    herolist = [hero1, hero2, hero3, hero4]

    choices = []
    for h, otherheroes in pluckfrom(herolist):
        name, chat1, chat2 = h['name'], h['chat1'], h['chat2']

        for chat in [chat1, chat2]:
            gain = sum([o[chat] for o in otherheroes])
            choices.append((gain, name, chat))

    return sorted(choices, reverse=True)


def filter_dict(src, criteria):
    def accept(hero):
        for attrib, accepts in criteria.items():
            if hero.get(attrib) not in accepts:
                return False
        return True

    return {k: v for k, v in src.items() if accept(v)}


def flag2whitelist(arg):
    if not arg.startswith('?'):
        return None

    # Best-effort to find flags
    arg = ''.join(arg.split())
    constraints = set(Constraint.read(x) for x in arg.split('?') if x)
    if not constraints:
        return None

    # Build whitelist from given constraints
    whitelist = defaultdict(list)
    for con in constraints:
        if con in 'knight,mage,ranger,soul weaver,thief,warrior'.split(','):
            whitelist['Class'].append(con)

        elif con == 'defbreak':
            whitelist['HasDefenseDown'].append(True)

    return whitelist


def validate_team(*heronames):
    # Check duplicates
    count = len(heronames)
    heronames = list(set(heronames))
    if len(heronames) != count:
        return False

    # Check spec. change
    for name, others in pluckfrom(heronames):
        scname = SPEC_CHANGE.get(name)
        if (scname) and (scname in others):
            return False

    return True


def generate_teams(*whitelists):
    heroes = HEROES.copy()
    namepools = [list(filter_dict(heroes, wlist).keys())
                 for wlist in whitelists]
    for team in itertools.product(*namepools):
        if validate_team(*team):
            print(team)
            yield team


def query(*args):
    whitelists = []
    for arg in args:
        whitelist = flag2whitelist(arg)
        if whitelist:
            whitelists.append(whitelist)
        else:
            hero = HEROES[arg]
            if hero:
                whitelists.append({'Name': [hero['Name']]})

    teams = list(generate_teams(*whitelists))
    return teams, whitelists




if __name__ == '__main__':
    heroes = load()
