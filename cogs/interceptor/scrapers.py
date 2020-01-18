import json

import bs4
import requests


def get_soup(url):
    soup = url
    if isinstance(url, bs4.BeautifulSoup):
        return url

    res = requests.get(str(url))
    if not res.ok:
        return None
    return bs4.BeautifulSoup(res.text, 'html.parser')


def twitter(url):
    soup = get_soup(url)

    container = soup.find('div', class_='AdaptiveMediaOuterContainer')
    if not container:
        return None

    img = container.find('img')
    if not (img and isinstance(img, bs4.element.Tag)):
        return None

    return img['src'] or None


def pixiv(pic_id):
    url = f'https://www.pixiv.net/en/artworks/{pic_id}'

    soup = get_soup(url)
    metas = soup.head.find_all('meta')
    if not metas:
        return None

    content = metas[-1]
    if not content:
        return None

    j = json.loads(content['content'])

    if not 'illust' in j:
        return None

    for val in j['illust'].values():
        if ('urls' in val) and ('original' in val['urls']):
            return val['urls']['original']
