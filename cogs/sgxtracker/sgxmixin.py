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
        #   label author mediaType name date url filemime
        self.data = json_data

    @property
    def articleid(self):
        unix_secs = int(self.timestamp.timestamp())
        return f'{self.title}-{unix_secs}'

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
            'name': self.data['author'],
        }

    @property
    def timestamp(self) -> datetime.datetime:
        dt = datetime.datetime.fromtimestamp(self.data['date'])
        return dt

    @property
    def time_since_posted(self) -> datetime.timedelta:
        utc = datetime.timezone.utc
        timenow = datetime.datetime.now().astimezone(utc)
        timestamp = self.timestamp.astimezone(utc)
        diff = timenow - timestamp
        # print(self.articleid, diff)
        return diff

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


    @classmethod
    def get_json_data(cls, soup):
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


    @classmethod
    def read_page_data(cls, page_data):
        """Parses the data from json into data for each post

        Each month is extracted from the accordion and parsed into posts with
        parse_accordion_month().

        Structure (simplified):
            - section
                - author
                - accordion
                    - Feb 2020: post3, post4
                    - Jan 2020: post1, post2
        """
        content = page_data['data']['route']['data']['data']
        # page_title = content['title']

        posts = []
        for section in content['widgets']:
            # 1 section => 1 author => 1 accordion => multiple months
            author = section['data']['title']  # Maybank Kim Eng Securities, etc
            accordion = section['data'].get('accordionItems')

            if not accordion:
                continue

            posts = []
            for month in accordion:
                # Push each dlinfo in each month in output posts:
                dlinfos = cls.parse_accordion_month(author, month)
                if not dlinfos:
                    continue
                posts.extend(dlinfos)
        return posts


    @classmethod
    def parse_accordion_month(cls, author, accordion_month):
        """Extracts posts for each month in the accordion"""
        m_label = accordion_month['data']['itemTitle'] # => May 2020 etc
        widgets = accordion_month['data']['widgets']
        if not widgets:
            return None

        downloadables = []
        for dl in widgets[0].get('data', {}).get('downloadItems', []):
            dldata = dl.get('data')
            if not dldata:
                continue
            if not dldata.get('label'):
                continue
            if not dldata.get('file'):
                continue
            downloadables.append(dldata)
        if not downloadables:
            return None

        # Flatten the structure of each downloadable entry
        posts = []
        for dldata in downloadables:
            label = dldata['label']
            dlinfo = dldata['file']['data']
            dlinfo['url'] = dlinfo['file']['data']['url']
            dlinfo['filemime'] = dlinfo['file']['data']['filemime']
            dlinfo['label'] = label
            dlinfo['author'] = author
            # Sanity check
            try:
                keys = 'label author mediaType name date url filemime'
                assert all([k in dlinfo for k in keys.split()])
            except AssertionError:
                continue
            posts.append(dlinfo)

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
            #   label author mediaType name date url filemime

            for dldata in posts_data:
                post = SgxResearchPost(dldata)
                posts.append(post)

        if posts:
            new_posts = self.filtered(posts)
            await self.handle_new_posts(new_posts)

        return True


    @classmethod
    def filtered(cls,
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
