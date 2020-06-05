# -*- coding: utf-8 -*-

import logging
import urllib.parse as urllib_parse

from discord import Embed
from discord.utils import escape_markdown

from .client import CLIENT
from .config import DAN_COLOUR, DAN_URL_STUB, DAN_SEARCH_STUB


log = logging.getLogger(__name__)


def escape_tag(s):
    return escape_markdown(s.replace('_', ' '))


def merge_string(strlist, maxlen, delim=', ', end='...', key=None):
    maxlen -= len(end)
    dlen = len(delim)

    if key:
        strlist = [key(string) for string in strlist]

    num_insert = 0
    cumu_len = 0

    for string in strlist:
        strlen = len(string) + dlen
        if (strlen + cumu_len) > maxlen:
            break

        num_insert += 1
        cumu_len += strlen

    joined = delim.join(strlist[:num_insert])
    end = end if num_insert < len(strlist) else ''
    return joined + end, num_insert


def make_post_title(post):
    max_title_len = 256

    artist_tag = post.get('tag_string_artist', '')
    artist = escape_tag(artist_tag.replace(' ', ', '))
    drawnby = f' drawn by {artist}' if artist else ''

    char_len = max_title_len - len(drawnby) - len(' and 9999 others')

    chars = post['tag_string_character'].split()
    chars_str, num_added = merge_string(chars, char_len, end='', key=escape_tag)

    # Check if no chars added, this means the first name is already too long
    if chars and num_added == 0:
        trunc_len = char_len - len('...')
        char = escape_tag(characters_to_add[0])
        char = char[:trunc_len]
        chars_str = char + '...'

    remaining = ''
    num_left = len(chars) - num_added
    if num_left > 0:
        s = 's' if num_left != 1 else ''
        remaining = f' and {num_left} other{s}'

    title = f'{chars_str}{remaining}{drawnby}' or '(untitled)'
    assert(len(title) <= max_title_len)
    return title


def get_tag_counts(*tags):
    # Fetch the count for at most 20 tags at once
    # Map tagname -> tagcount
    # Output a list by looking up the tagnames in the name->count mapping
    step = 20
    taglist = {}
    for i in range(len(tags) // step + 1):
        p, q = step * i, step * (i + 1)
        batch_tagstr = ','.join(tags[p:q])
        batch = {
            t.get('name'): t.get('post_count', 0)
            for t in CLIENT.tag_list(name_comma=batch_tagstr)
        }
        taglist.update(batch)

    return [taglist.get(name, 0) for name in tags]


def make_field_val(*tags):
    def format_val(tagname, postcount):
        tagname = escape_tag(tagname)
        link = DAN_SEARCH_STUB + urllib_parse.quote(tagname)
        return f'[`{tagname}`]({link})({postcount})'

    field_size = 512  # 1024 is the official limit but be conservative
    if not tags:
        return '(none)'

    counts = get_tag_counts(*tags)
    formatted = [format_val(name, cnt) for name, cnt in zip(tags, counts)]

    field_str, num_added = merge_string(formatted,
                                        maxlen=field_size - len(' and 9999 others'),
                                        delim='\n',
                                        end='')

    remain = len(tags) - num_added
    s = '' if remain == 1 else 's'
    end = str('\nand %d other%s' % (remain, s)) if remain else ''

    return field_str + end


def make_embed(post, img_url, tags_str, footer=True):
    md5 = post.get('md5', '(none)')
    log.info(f'Making embed for post: img_url={img_url}, md5={md5}')

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

    return embed
