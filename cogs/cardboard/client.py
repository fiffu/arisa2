from pybooru import Danbooru

import appconfig

USER = appconfig.fetch('DANBOORU', 'USER')
API_KEY = appconfig.fetch('DANBOORU', 'API_KEY')


CLIENT = Danbooru(
    'danbooru',
    username=USER,
    api_key=API_KEY
)
