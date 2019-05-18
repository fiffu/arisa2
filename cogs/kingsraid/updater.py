import asyncio
from base64 import b64decode
from collections import defaultdict
import json
from os.path import abspath, dirname, getmtime, join

import aiohttp
import requests

import config
from utils import anypartial
from utils.scraping import pull_pages


basedir = abspath(dirname(__file__))

JSON_DATA = join(basedir, "krdata.json")
DATAURL = "https://raw.githubusercontent.com/duckness/Mask-of-Goblin/master/src/data.json"

JSON_ENG = join(basedir, "krenglish.json")
# ENGURL = "https://raw.githubusercontent.com/duckness/Mask-of-Goblin/master/src/store/i18n/English.json"
MOG_GITAPI_STUB = 'https://api.github.com/repos/duckness/Mask-of-Goblin/contents/'
ENG_PATH = 'public/i18n/English/'

GITHUB_USER = config.fetch('GITHUB', 'USER')
GITHUB_AUTH = config.fetch('GITHUB', 'SECRET')


def read_json(fp):
    with open(fp, 'r', encoding='utf-8') as f:
        return json.loads(f.read())


def read_files():
    return read_json(JSON_DATA), read_json(JSON_ENG)


def make_auth(user=GITHUB_USER, pw=GITHUB_AUTH, aio=False):
    if aio:
        return aiohttp.BasicAuth(user, password=pw)
    else:
        return requests.auth.HTTPBasicAuth(user, password=pw)


def fetch_mog_json(path):
    try:
        res = requests.get(MOG_GITAPI_STUB + path, auth=make_auth())
        assert res.ok
        return res.json()
    except Exception as e:
        raise RuntimeError(f'failed to collect {MOG_GITAPI_STUB + path}')


async def pull_mog_eng_json(loop):
    out = defaultdict(dict)

    # Fetch root dir for english translation
    root = fetch_mog_json(ENG_PATH)

    # Walk dir, extract folder/file names, filepath stubs for json resources
    for folder in [x for x in root if x['type'] == 'dir']:
        subdir = fetch_mog_json(folder['path'])
        filepaths = {
            f['name'].split('.')[0]: f['path']
            for f in subdir
            if (f['name'].endswith('.json') 
                and not f['name'].startswith('names'))
        }
        out[folder['name']] = filepaths

    # Derive absolute urls for resources, map to folder and file names
    url_to_folder_file = {}
    for foldern, files in out.items():
        for filen, filep in files.items():
            url = MOG_GITAPI_STUB + filep
            url_to_folder_file[url] = (foldern, filen)
            
    results = await pull_pages(
        loop, url_to_folder_file.keys(), auth=make_auth(aio=True))
    
    # Unflatten results to match the original 2-deep nested structure
    for url, res in results:
        j = await res.json()
        foldern, filen = url_to_folder_file[url]
        out[foldern][filen] = json.loads(b64decode(j['content']))

    return out


async def update_eng(loop):
    data = await pull_mog_eng_json(loop)
    with open(JSON_ENG, 'w', encoding='utf-8') as f:
        f.write(json.dumps(data, indent='  '))


async def update_data(loop):
    req = requests.get(DATAURL)
    if not req.ok:
        return
    with open(JSON_DATA, 'w', encoding='utf-8') as f:
        f.write(req.text)


async def update_dataset(loop):
    await update_eng(loop)
    await update_data(loop)
