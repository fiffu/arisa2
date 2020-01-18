"""Legacy code fragments"""


### Legacy data loader using csv data. Preserved if we ever need it
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

### This was originally meant to cache the best-performing heroes for a given
### chat option. Now depreciated
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
