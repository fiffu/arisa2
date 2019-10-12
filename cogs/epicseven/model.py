from collections import defaultdict
import itertools
import os.path
import json
import re
import warnings

import requests

from utils import DigestDict
from .specialtychange import SPEC_CHANGE


SRC = 'lab.json'
# JSON data gratefully obtained from epicseventools.com

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

# BEST_CHAT_YIELD_CACHE = dict()  # Map[str: List[Tuple[str, int]]]
# def best_candidates_for_option(chatoption, pool=None):
#     """
#     (chatoption: str, pool: dict) -> list(tuple(gain: int, heroname: str))
#     """
#     if pool:
#         gains = [(v[chatoption], k) for k, v in pool.items()]
#         return gains

#     if chatoption not in BEST_CHAT_YIELD_CACHE:
#         gains = [(v[chatoption], k) for k, v in HEROES.items()]
#         BEST_CHAT_YIELD_CACHE[chatoption] = sorted(gains, reverse=True)

#     return BEST_CHAT_YIELD_CACHE[chatoption]


def pluckfrom(iterable):
    for i, item in enumerate(iterable):
        yield item, iterable[0:i] + iterable[i + 1:]


def load_json(file):
    basedir = os.path.abspath(os.path.dirname(__file__))
    filepath = os.path.join(basedir, file)
    with open(filepath) as f:
        return json.load(f)


def load():
    global HEROES

    jsondata = load_json(SRC)

    heroes = DigestDict()
    for hero in jsondata:
        try:
            ok = all(list(hero.get(k) for k in ['Reactions', 'Options']))
            if not ok:
                continue
            hero.update(hero.pop('Reactions'))

            c1, c2 = hero.pop('Options')
            hero['chat1'] = c1
            hero['chat2'] = c2

            cls = hero['Class'].replace('-', ' ') # soul-weaver -> soul weaver
            hero['Class'] = cls

            key = hero['Name'].lower()
            heroes.add(key, hero)

        except BaseException as e:
            warnings.warn(f'Failed to parse {hero} ({e})')
            continue

    HEROES = heroes
    return heroes


def get_heroes():
    global HEROES
    if HEROES is None:
        HEROES = load()
    return HEROES


def calculate_morale(hero1, hero2, hero3=None, hero4=None):
    HEROES = get_heroes()

    herolist = [HEROES[h] for h in (hero1, hero2, hero3, hero4) if h]

    choices = []
    for h, otherheroes in pluckfrom(herolist):
        name, chat1, chat2 = h['Name'], h['chat1'], h['chat2']

        for chat in (chat1, chat2):
            gain = sum(o[chat] for o in otherheroes)
            choices.append((gain, name, chat))

    return sorted(choices, reverse=True)[:2]


def filter_dict(source, whitelist):
    """Subsets the source dict using criteria in the whitelist.

    The source dictionary will not be modified.
    """
    if not whitelist:
        return source

    def accept(hero):
        for attrib, accepts in whitelist.items():
            if hero.get(attrib) not in accepts:
                return False
        return True

    return {k: v for k, v in source.items() if accept(v)}


def flag_to_whitelist(arg):
    """Converts a string argument to a whitelist

    Each whitelist contains a set of rules to subset HEROES by. A whitelist is
    a dictionary of lists, created using flag_to_whitelist(). Each list
    contains a finite range of values for the key it is assigned to, that we
    want in the filtered output.
    """
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
    """False if duplicated heroes (same name, specialty change etc)"""
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


def pools_to_teams(pools, maxteamsize=4):
    if len(pools) <= maxteamsize:
        yield from itertools.product(*pools)
    else:
        # If there are many pools, iterate over combinations N pools
        # Then yield cartesian product of these N pools (N=maxteamsize)
        for combipools in itertools.combinations(pools, maxteamsize):
            yield from itertools.product(*combipools)


def generate_teams(*whitelists, maxteamsize=4):
    """Takes N whitelists and yields teams of N-long tuple(heroes); N <= 4

    If 3 whitelists (Map[str, List[Any]]) are provided, then each team yielded
    will have 3 heroes. The yielded team has to be valid according to
    validate_team().

    See also: flag_to_whitelist().
    """
    heroes = HEROES.copy()
    names = [list(filter_dict(heroes, wlist).keys())
             for wlist in whitelists]

    for team in pools_to_teams(names, maxteamsize=maxteamsize):
        if validate_team(*team):
            yield team


def query_to_pool(*args):
    """Parses queries into List[hero] and List[whitelistdict]"""
    HEROES = get_heroes()

    whitelists = []
    for arg in args:
        whitelist = flag_to_whitelist(arg)
        if whitelist:
            whitelists.append(whitelist)
        else:
            hero = HEROES[arg]
            if hero:
                whitelists.append({'Name': [hero['Name']]})
            else:
                whitelists.append(None)

    teams = list(generate_teams(*whitelists))
    return teams, whitelists


def calculator(*heronames, maxteams=50):
    res = []
    teams, whitelists = query_to_pool(*heronames)
    for team in teams:
        first, second = calculate_morale(*team)
        res.append((team, first, second))

    choices = sorted(res,
                     key=lambda tup: tup[1][0] + tup[2][0],
                     reverse=True)
    return choices[:maxteams], whitelists


if __name__ == '__main__':
    heroes = load()
