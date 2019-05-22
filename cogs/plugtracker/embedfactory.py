from discord import Embed

from .plugmixin import PlugPost


ATTRS_INHERITED_FROM_PLUGPOST = [
    'title',
    'url',
    'timestamp',
]


def new_plug_embed(topic, plugpost: PlugPost):
    try:
        kwargs = {
            attr: getattr(plugpost, attr)
            for attr in ATTRS_INHERITED_FROM_PLUGPOST
        }

        embed = Embed(**kwargs)

        embed.set_author(**plugpost.author)
        embed.set_image(url=plugpost.image_url)
        
        fname, furl = plugpost.forum_name, plugpost.forum_url
        forumlink = f'[{fname}]({furl})'
        embed.add_field(name='Posted in forum', value=forumlink)
        embed.set_footer(text='To stop receiving updates from this topic, '
                              f'type !stopann {topic}')
        return embed

    except Exception as e:
        raise e
        # return None
