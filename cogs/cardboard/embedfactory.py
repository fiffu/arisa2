# -*- coding: utf-8 -*-

import logging
import urllib.parse as urllib_parse

from discord import Embed
from discord.utils import escape_markdown

from .client import CLIENT
from .config import DAN_COLOUR, DAN_URL_STUB, DAN_SEARCH_STUB


log = logging.getLogger(__name__)


def make_post_title(post):
    max_title_len = 256

    artist = escape_markdown(post.get('tag_string_artist', ''))
    artist_str = ''
    if artist:
      artist_str = f' drawn by ' + post['tag_string_artist'].replace(' ', ', ')

    curr_len = len(artist) + len('``')
    characters_to_add = post['tag_string_character'].split()
    include_chars = []

    # Include chars in title until we run out of space
    while characters_to_add:
        next_char = escape_markdown(characters_to_add[0])
        if curr_len + len(f', {next_char} and 9999 others') > max_title_len:
            # Stop if next addition would exceed max title length
            break
        curr_len += len(next_char)
        include_chars.append(characters_to_add.pop(0))

    # Check if no chars included, but to_add list is still populated
    # This means the first name is already too long
    if (not include_chars) and characters_to_add:
        trunc_name_to = max_title_len - len('... and 0000 others')
        next_char = escape_markdown(characters_to_add.pop(0))
        next_char = next_char[:trunc_name_to]
        include_chars.append(f'{next_char}...')

    remaining = ''
    if characters_to_add:
        num_left = len(characters_to_add)
        s = 's' if num_left != 1 else ''
        remaining = f' and {num_left} other{s}'

    title = '{chars}{remaining}{drawnby}'.format(
        chars=', '.join(include_chars) if include_chars else '',
        remaining=remaining,
        drawnby=artist_str
    )
    title = title or '(untitled)'
    assert(len(title) <= max_title_len)

    return title


def get_tag_counts(*tags):
    tagstr = ','.join(tags)
    taglist = {
        t.get('name'): t.get('post_count', 0)
        for t in CLIENT.tag_list(name_comma=tagstr)
    }
    return [taglist.get(name, 0) for name in tags]


def make_embed(post, img_url, tags_str, footer=True):
    def make_field_val(*tags):
        if not tags:
            return '(none)'
        counts = get_tag_counts(*tags)
        return '\n'.join(
            f'[`{name}`]({DAN_SEARCH_STUB + urllib_parse.quote(name)}) ({cnt})'
            for name, cnt in zip(tags, counts)
        )

    title = make_post_title(post)
    embed = Embed(title=title,
                  color=DAN_COLOUR)
    embed.set_image(url=img_url)

    artists = post['tag_string_artist'].split()
    artist_val = make_field_val(*artists)
    s = 's' if len(artists) > 1 else ''
    embed.add_field(name=f'Artist{s}:', value=artist_val, inline=True)

    copyrights = post['tag_string_copyright'].split()
    copyright_val = make_field_val(*copyrights)
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

    if footer:
        embed.set_footer(text='Matched against tag: ' + tags_str.split()[0])

    md5 = post.get('md5', '(none)')
    log.info(f'Generate embed for post: img_url={img_url}, md5={md5}')

    return embed
