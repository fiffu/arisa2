from pybooru import Danbooru

import appconfig

USER = appconfig.fetch('DANBOORU', 'USER')
API_KEY = appconfig.fetch('DANBOORU', 'API_KEY')

class DanbooruCustom(Danbooru):
    """Override DanbooruApi_Mixin.tag_list to monkey-patch name_comma param"""
    def tag_list(self, name_matches=None, name=None, name_comma=None, category=None,
                 hide_empty=None, has_wiki=None, has_artist=None, order=None):
        """Get a list of tags.
        Parameters:
            name_matches (str): Can be: part or full name. Supports patterns.
            name (str): Allows searching for single tag with exact given name.
            name_comma (str): Allows searching for multiple tags with exact 
                              given names, separated by commas. e.g. 
                              search[name_comma]=touhou,original,k-on! would 
                              return the three listed tags.
            category (str): Can be: 0, 1, 3, 4 (general, artist, copyright,
                            character respectively).
            hide_empty (str): Can be: yes, no. Excludes tags with 0 posts
                              when "yes".
            has_wiki (str): Can be: yes, no.
            has_artist (str): Can be: yes, no.
            order (str): Can be: name, date, count.
        """
        params = {
            'search[name_matches]': name_matches,
            'search[name]': name,
            'search[name_comma]': name_comma,
            'search[category]': category,
            'search[hide_empty]': hide_empty,
            'search[has_wiki]': has_wiki,
            'search[has_artist]': has_artist,
            'search[order]': order
        }
        return self._get('tags.json', params)


CLIENT = DanbooruCustom(
    'danbooru',
    username=USER,
    api_key=API_KEY
)

# For some reason Pybooru uses http instead of https for API
CLIENT.site_url = 'https://danbooru.donmai.us'
