import datetime
import json
import logging
from typing import Sequence

from bs4 import BeautifulSoup
from discord import Embed

# from cogs.tracking.config import TRACKER_UPDATE_INTERVAL_SECS

TRACKER_UPDATE_INTERVAL_SECS = 30 * 60  # every 30 min


log = logging.getLogger(__name__)



class SgxResearchPost:
    page_name = 'Analyst Research'
    page_url = 'https://www.sgx.com/research-education/analyst-research'
    page_thumbnail = 'https://mylogin.sgx.com/mylogin/XUI/images/sgx-logo.png'

    def __init__(self, json_data):
        # json_data is a dict with these keys:
        #   label source mediaType name date url filemime
        self.data = json_data

    @property
    def articleid(self):
        return f'{self.title}-{self.timestamp}'

    @property
    def title(self):
        return self.data['label']

    @property
    def url(self):
        return self.data['url']

    @property
    def image_url(self):
        return self.page_thumbnail

    @property
    def author(self):
        return {
            'name': self.data['source'],
        }

    @property
    def timestamp(self) -> datetime.datetime:
        dt = datetime.datetime.fromtimestamp(self.data['date'])
        return dt

    @property
    def time_since_posted(self) -> datetime.timedelta:
        timenow = datetime.datetime.now().astimezone(datetime.timezone.utc)
        return timenow - self.timestamp

    def to_embed(self, topic):
        try:
            kwargs = {attr: getattr(self, attr)
                      for attr in ('title', 'url', 'timestamp')}
            embed = Embed(**kwargs)

            embed.set_author(**self.author)
            embed.set_thumbnail(url=self.image_url)

            pname, purl = self.page_name, self.page_url
            pagelink = f'[{pname}]({purl})'
            embed.add_field(name='Update from', value=pagelink)
            embed.set_footer(text='To stop updates from this topic, '
                                  f'type !untrack {topic}')
            return embed

        except Exception as e:
            log.exception(e)
            raise e


    def __repr__(self):
        return f'<SgxResearchPost {self.articleid}: {self.title}>'


class SgxMixin:
    """Mixin to be used with discord.ext.command.Cog"""

    sgx_page_name_urls = {
        'Analyst Research': 
            'https://www.sgx.com/research-education/analyst-research'
    }

    async def handle_new_posts(self, new_posts: Sequence[SgxResearchPost]):
        topic = self.topic
        pscog = self.pubsubcog

        if not pscog:
            log.warning('PublishSubscribe not found, unable to publish '
                        '"%s" announces to channels', self.topic)
            return

        channelids = await pscog.get_channelids_by_topic(topic)
        if not channelids:
            log.info('New updates received on topic "%s", but no '
                     'subscribers to be notified.', self.topic)
            return


        posts = sorted(new_posts, key=lambda p: p.timestamp)
        if not posts:
            return

        s = 's' if len(posts) != 1 else ''
        log.info('%s new post%s for topic "%s"', len(posts), s, topic)

        sendargs = [
            dict(content=None, embed=post.to_embed(self.topic))
            for post in posts
        ]
        await pscog.push_to_topic(self.topic, sendargs)


    @staticmethod
    def get_json_data(soup):
        """SGX stores page data in a json payload stashed in a <script> tag

        Their site app reads this data and renders to the page.
        """
        scripts = [
            elem.text.strip() for elem in soup.find_all('script')
            if len(elem.text) > 100000
        ]
        if not scripts:
            return None
        script = scripts[0]
        js = script[len('window._sgxComApp_pageData = '):-1]  # -1 is trailing ;
        return json.loads(js)


    @staticmethod
    def read_page_data(page_data):
        content = page_data['data']['route']['data']['data']

        # page_title = content['title']

        posts = []
        for section in content['widgets']:
            accordion = section['data'].get('accordionItems')
            if not accordion:
                continue

            source = section['data']['title']  # Maybank Kim Eng Securities, etc
            posts = []
            for month in accordion:
                # month['itemTitle'] => May 2020 etc
                downloadables = [sec['downloadItems']
                                 for sec in month['data']['widgets']
                                 if 'downloadItems' in sec]
                if not downloadables:
                    continue

                # Flatten the structure of each downloadable entry
                for dlable in downloadables:
                    label = dlable['data']['label']
                    dldata = dlable['data']['file']

                    dldata['label'] = label
                    dldata['source'] = source
                    dldata['url'] = dldata['file']['data']['url']
                    dldata['filemime'] = dldata['file']['data']['filemime']

                    del dldata['file']

                    # Sanity check
                    try:
                        keys = 'label source mediaType name date url filemime'
                        assert all([k in dldata for k in keys.split()])
                    except AssertionError:
                        continue

                    # Push each dldata in each month in the accordion:
                    posts.append(dldata)
        return posts


    async def do_work(self) -> Sequence[SgxResearchPost]:
        #log.info(f'Checking "{self.topic}" for updates...')
        pages = await self.pull_pages()

        posts = []

        for page in pages:
            soup = BeautifulSoup(page, 'html.parser')

            page_data = self.get_json_data(soup)
            posts_data = self.read_page_data(page_data)

            # posts_data is a List[dict] each with these keys:
            #   label source mediaType name date url filemime

            for dldata in posts_data:
                post = SgxResearchPost(dldata)
                posts.append(post)

        if posts:
            new_posts = self.filtered(posts)
            await self.handle_new_posts(new_posts)

        return True


    def filtered(self,
                 posts: Sequence[SgxResearchPost],
                 cutoff_secs: int = TRACKER_UPDATE_INTERVAL_SECS):
        new_posts = []
        for post in posts:
            time_delta = post.time_since_posted
            time_delta_secs = time_delta.total_seconds()
            if time_delta_secs < cutoff_secs:
                new_posts.append(post)
        return new_posts


    async def pull_pages(self):
        urls = list(self.sgx_page_name_urls.values())

        resps = []
        for response in await self.batch_get_urls(self.bot.loop, *urls):
            resps.append(await response.text())

        return resps
