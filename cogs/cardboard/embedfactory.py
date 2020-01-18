# -*- coding: utf-8 -*-

import logging
import urllib.parse as urllib_parse

from discord import Embed
from discord.utils import escape_markdown

from .config import DAN_COLOUR, DAN_URL_STUB, DAN_SEARCH_STUB

log = logging.getLogger(__name__)


def make_post_title(post):
    artist_str = escape_markdown(post.get('tag_string_artist', ''))
    artist = ''
    if artist_str:
      artists = post['tag_string_artist'].replace(' ', ', ')
      artist = f" drawn by {artists}"

    curr_len = len(artist) + len('``')

    *characters, = post['tag_string_character'].split()
    include_chars = []
    unadded = len(characters)
    for char in characters:
        char = escape_markdown(char)
        if (curr_len + len(' and 999 others')) > 256:
            include_chars.pop()
            s = 's' if unadded > 1 else ''
            others = f'and {unadded} other{s}'
            include_chars.append(others)
            break
        else:
            if (curr_len + len(char)) > 256:
                excess = curr_len + len(char) - 256 + 3
                include_chars.append(char[:-excess] + '...')
                break
            else:
                include_chars.append(char)
                curr_len += (len(char) + len(', '))
                unadded -= 1

    char_string = ', '.join(include_chars)
    title = f'{char_string}{artist}'
    title = title or '(untitled)'
    assert(len(title) <= 256)

    return title


def make_embed(post, img_url, tags_str):
    title = make_post_title(post)
    embed = Embed(title=title,
                  color=DAN_COLOUR)
    embed.set_image(url=img_url)

    artist = post['tag_string_artist'].split() or ['(none)']
    s = 's' if len(artist) > 1 else ''
    artist_val = '\n'.join(
        f'[`{a}`]({DAN_SEARCH_STUB + urllib_parse.quote(a)})'
        for a in artist
    )
    embed.add_field(name=f'Artist{s}:', value=artist_val, inline=True)

    copyrights = post['tag_string_copyright'].split() or ['(none)']
    copyright_val = '\n'.join(
        f'[`{a}`]({DAN_SEARCH_STUB + urllib_parse.quote(a)})'
        for a in copyrights
    )
    embed.add_field(name=f'Source:', value=copyright_val, inline=True)

    page_url = DAN_URL_STUB + '/posts/' + str(post['id'])
    search_url = DAN_SEARCH_STUB + urllib_parse.quote(tags_str)
    links_val = ' · '.join(
        f'[{k}]({v})'
        for k, v in [
            ('pic', img_url),
            ('post', page_url),
            ('search', search_url),
        ]
    )
    embed.add_field(name='Links:', value=links_val, inline=False)

    embed.set_footer(text='Matched against tag: ' + tags_str.split()[0])

    md5 = post.get('md5', '(none)')
    log.info(f'Generate embed for post: img_url={img_url}, md5={md5}')

    return embed
