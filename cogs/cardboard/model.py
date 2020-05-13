import logging
import random
from typing import List, Tuple

from bs4 import BeautifulSoup
import requests

from utils.memoized import memoized
from . import config
from .client import CLIENT
from .tag import Parser

log = logging.getLogger(__name__)

# Custom typing
Post = dict
Url = str

# Consts
POSTS_PER_QUERY = config.POSTS_PER_QUERY
DAN_URL_STUB = config.DAN_URL_STUB

client = CLIENT


VETO = config.VETO
FLOATS = config.FLOATS
SINKS = config.SINKS
EXCLUDE = set(config.EXCLUDE_POSTS_TAGGED_WITH)

@memoized
def dumb_search(search_string):
    return client.post_list(tags=search_string, limit=POSTS_PER_QUERY)


def process_tags(taglist) -> Tuple[List, List, List, List]:
    taglist = sorted(taglist, key=lambda t: len(t['name']))

    veto = VETO
    floats = FLOATS
    sinks = SINKS

    floated, regular, sunk, vetoed = [], [], [], []
    for tag in taglist:
        name = tag['name']

        if name in veto:
            vetoed.append(tag)
            log.info(f'Discarding vetoed tag "{name}"')
            continue

        for x in sinks:
            if x in name:
                sunk.append(tag)
                break
        else:
            # For-else means proceed here if tag was not sunken
            for x in floats:
                if x in name:
                    floated.append(tag)
                    break
            else:
                regular.append(tag)

    sorted_tags = floated + regular + sunk
    return sorted_tags, floated, sunk, vetoed


async def fetch_tag_matches(candidate: str) -> Tuple[List, List, List, List]:
    taglist = client.tag_list(name_matches=candidate)
    if (not taglist) and (not candidate.endswith('*')):
        candidate += '*'
    taglist = client.tag_list(name_matches=candidate)
    return process_tags(taglist)


async def prep_search_string(candidates: List[str]) -> str:
    search_string = ' '.join(candidates)
    if len(candidates) == 1:
        tagmatches, *_ = await fetch_tag_matches(search_string)
        if len(tagmatches) > 0:
            search_string = tagmatches[0]['name']
    return search_string


async def smart_search(query, explicit_rating) -> List[Post]:
    """Does some parsing on the query before searching.

    Args
    query: str - search query to parse
    explicit_rating: str - should match /-?[eqs]/ if provided, which is parsed
                           into extra search constraint as /-?rating:(e|q|s)/
    """
    # query as single tag
    cands, alias_applied = Parser(spaces_to_underscore=True).parse(query)
    search_string = await prep_search_string(cands)

    # inject rating
    if explicit_rating:
        minus = ''
        rating = 's'

        if explicit_rating[-1] in ['e', 'q', 's']:
            rating = explicit_rating[-1]
            if explicit_rating.startswith('-'):
                minus = '-'

        add_to_search = f'{minus}rating:{rating}'

        search_string += (' ' + add_to_search)

    posts = dumb_search(search_string)
    return posts, search_string


async def select_posts(posts, num_to_return=1) -> List[Tuple[Post, Url]]:
    # Cull input to cap at 100 (default posts per query)
    # Long sequences greatly increase time to shuffle
    posts = posts[:POSTS_PER_QUERY]
    random.shuffle(posts)

    output = []
    for post in posts:
        if EXCLUDE.intersection(set(post['tag_string'].split())):
            continue

        imgurl = get_image_url(post)
        if imgurl:
            output.append((post, imgurl))
        if len(output) == num_to_return:
            break

    return output


def is_media_url(url):
    for ext in ['png', 'jpg', 'jpeg', 'gif']:
        # WebM doesn't show on embed preview
        if str(url).endswith('.' + ext):
            return True
    return False


def get_image_url(post):
    # Simply return if URL is in the json
    img_url = ''
    for field in ['file_url', 'large_file_url', 'preview_file_url']:
        if is_media_url(post.get(field, '')):
            url = post[field]
            img_url = (DAN_URL_STUB if 'http' not in url else '') + url
            break

    if not img_url:
        # Otherwise scrape the post for the image url
        # Give up in the unlikely case this post has no id
        if 'id' not in post:
            return None
        img_url = pull_img_url(post['id'])

    # Monkey patch for Danbooru sometimes breaking image urls
    if '//data/' in img_url:
        img_url = img_url.replace('//data/', '/data/')

    return img_url


@memoized
def pull_img_url(postid):
    postid = str(postid)
    r = requests.get(DAN_URL_STUB + '/posts/' + postid)
    retries = 0
    while (not r.ok) and (retries < 3):
        retries += 1
        r = requests.get(DAN_URL_STUB + '/posts/' + postid)
    if not r.ok:
        return ''

    soup = BeautifulSoup(r.text, 'html.parser')
    img = soup.find('img', {'id': 'image'})
    if not img:
        return ''

    img_url = img['src']

    return img_url
