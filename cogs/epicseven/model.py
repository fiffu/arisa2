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

HEROES = None



class BadConstraintError(AttributeError):
    def __init__(self, val):
        super().__init__("no Constraint matching '{val}'")
        self.val = val


class Constraint:
    keys = 'any,defbreak,knight,mage,ranger,soul weaver,thief,warrior'
    flagsdict = DigestDict()
    for key in keys.split(','):
        flagsdict[key] = key
    flagsdict[''] = 'any'

    @classmethod
    def read(cls, arg):
        return cls.flagsdict[arg]

    def __getitem__(self, key):
        val = self.flagsdict[key]
        if not val:
            raise BadConstraintError(val)
        return val

    def __getattr__(self, attr):
        return self[attr]
Constraint = Constraint()


def pluckfrom(iterable):
    """ABC -> (A,BC), (B,AC), (C,AB)"""
    for i, item in enumerate(iterable):
        yield item, iterable[0:i] + iterable[i + 1:]


def load_json(file):
    """Loads a json file in the same dir as this module."""
    basedir = os.path.abspath(os.path.dirname(__file__))
    filepath = os.path.join(basedir, file)
    with open(filepath) as f:
        return json.load(f)


def load():
    """Loads hero data into the global HEROES cache"""
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
    """Gets and initializes global cache if it is empty"""
    global HEROES
    if HEROES is None:
        HEROES = load()
    return HEROES


def calculate_morale(hero1, hero2, hero3=None, hero4=None):
    """Returns the top two options"""
    HEROES = get_heroes()

    herolist = [HEROES[h] for h in (hero1, hero2, hero3, hero4) if h]

    choices = []
    for h, otherheroes in pluckfrom(herolist):
        name, chat1, chat2 = h['Name'], h['chat1'], h['chat2']

        for topic in (chat1, chat2):
            gain = sum(o[topic] for o in otherheroes)
            choices.append((gain, name, topic))

    best, *others = sorted(choices, reverse=True)
    top2 = [best]
    for other in others:
        # `other` and `best` are tuples of (gain, name, topic)
        # 2nd topic chosen be same as the topic of `best`
        if other[-1] != best[-1]:
            top2.append(other)
            break
    return top2


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
    constraints = set(Constraint[x] for x in arg.split('?') if x)

    if not constraints:
        return None

    # Build whitelist from given constraints
    whitelist = defaultdict(list)
    for con in constraints:
        if con in 'knight,mage,ranger,soul weaver,thief,warrior'.split(','):
            whitelist['Class'].append(con)

        elif con == 'defbreak':
            whitelist['HasDefenseDown'].append(True)

        elif con in ['', 'any']:
            continue

        else:
            raise BadConstraintError(con)

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


def pools_to_teams(pools, combisize=4):
    """Combines pools into combisize, then yields cart. product of each combi.

    Each 'pool' is a sequence. This function takes a list of pools, then
    groups them by taking combinations of pools. Each combination will
    consist of up to `combisize` pools. Next, the cartesian product of the
    pools in each combination is yielded.

    This function returns a generator yielding tuples of length <= combisize.
    The tuple values are elements from the pools, not the pools.

    Current behaviour is O^n, n=len(pools). It is significantly slow when
    more than two of the `pools` consist of the entirety of HEROES
    """
    if len(pools) <= combisize:
        yield from itertools.product(*pools)
    else:
        # If there are many pools, iterate over combinations N pools
        # Then yield cartesian product of these N pools (N=combisize)
        for combination in itertools.combinations(pools, combisize):
            yield from itertools.product(*combination)


def generate_teams(*whitelists, maxteamsize=4):
    """Takes N whitelists and yields teams of N-long tuple(heroes); N <= 4

    If 3 whitelists (Map[str, List[Any]]) are provided, then each team yielded
    will have 3 heroes. The yielded team has to be valid according to
    validate_team().

    See also: flag_to_whitelist().
    """
    names = [list(filter_dict(HEROES, wlist).keys())
             for wlist in whitelists]

    for team in pools_to_teams(names, combisize=maxteamsize):
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
    choices = []
    max_gain = 0
    teams, whitelists = query_to_pool(*heronames)
    for team in teams:
        if len(choices) >= maxteams:
            break
        first, second = calculate_morale(*team)
        gain = first[0] + second[0]
        if gain >= max_gain:
            choices.insert(0, (team, first, second))
            max_gain = gain

    return choices, whitelists


if __name__ == '__main__':
    heroes = load()
