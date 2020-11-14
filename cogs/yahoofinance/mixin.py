# -*- coding: utf-8 -*-

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import logging
from typing import List, Mapping

from discord import Embed

log = logging.getLogger(__name__)

# Check every 10 min whether we are near midnight, if yes then trigger update
TRACKER_UPDATE_INTERVAL_MINS = 10
WIGGLE_ROOM_MINS = TRACKER_UPDATE_INTERVAL_MINS // 2

CACHED = {}

Unicode = SimpleNamespace(**{
    'ARROW_UP':   '▲',
    'BAR':        '─',  # \U00002500: BOX DRAWINGS LIGHT HORIZONTAL
    'DIAMOND':    '◆',
    'ARROW_DOWN': '▼',
    'EN_SPACE':   ' ',
    'DOT':        '·',
})

GREEN = 0x006400
ORANGE = 0xB36200


def rounded(n, places=3) -> str:
    s = '{:.0%df}' % places
    return s.format(n)


def thousands(number, places=3, joiner=',', decimalpt='.') -> str:
    p = places
    n, *dec = str(number).split('.')

    chunks = []
    while len(n) > p:
        n, chunk = n[:-p], n[-p:]
        chunks.append(chunk)
    chunks.append(n)

    out = joiner.join(chunks[::-1])
    if dec:
        out += decimalpt
        out += dec[0]
    return out


def errorformat(err):
    cls = err.__class__.__name__
    msg = str(err)
    return f'{cls}: {msg}'


class TickerToday:
    URL_STUB = 'https://sg.finance.yahoo.com/quote/'

    def __init__(self, symbol, name, data):
        self.name = name
        self.symbol = symbol.upper()
        self._timestamp = None

        for attr, value in data.items():
            setattr(self, attr, value)

        # Calculate and store direction
        self._diff = 0
        self._direction = 0

        close_quote = self.on_close['quote']
        open_quote = self.on_open['quote']
        diff = close_quote - open_quote

        # Express as percent, round to 2 d.p.
        rnd = lambda n: rounded(abs(n) / open_quote * 100, places=2)
        if rnd(diff) != rnd(0):
            self._diff = diff
            self._direction = 1 if diff > 0 else -1

    def by_direction(self, decrease, nochange, increase):
        direc = self._direction
        if not direc:
            return nochange
        return decrease if direc < 0 else increase

    @property
    def cachekey(self):
        time = self.timestamp.strftime('%d-%b-%Y %H:%M %Z').strip()
        return f'{self.symbol} {time}'

    @property
    def title(self):
        return f'{self.name} ({self.symbol})'

    @property
    def url(self):
        return self.URL_STUB + self.symbol.lower()

    @property
    def author(self):
        return {
            'name': 'Yahoo Finance',
            'url': self.URL_STUB
        }

    @property
    def timestamp(self) -> datetime:
        if self._timestamp:
            return self._timestamp
        timestamp = self.trading_period[1]
        return datetime.fromtimestamp(timestamp)

    @timestamp.setter
    def timestamp(self, timestamp):
        self._timestamp = timestamp

    @property
    def description(self):
        close_quote = self.on_close['quote']
        open_quote = self.on_open['quote']
        desc = f"Closed at __**{thousands(rounded(close_quote))}**__"

        diff = self._diff
        if diff:
            arrow = self.by_direction(Unicode.ARROW_DOWN, None, Unicode.ARROW_UP)
            sign = self.by_direction('-', None, '+')
            diffstr = rounded(abs(diff))
            diff_pct = rounded(abs(diff) / open_quote * 100, places=2)
            desc += f' {arrow}{Unicode.EN_SPACE}{sign}{diffstr} ({sign}{diff_pct}%)'

        return desc

    @property
    def colour(self):
        return self.by_direction(ORANGE, 0, GREEN)

    @property
    def fields(self):
        # {
        #     'on_open':
        #         {'time': times[0] - offset, 'quote': opens[0] - offset},
        #     'on_close':
        #         {'time': times[-1] - offset, 'quote': closes[-1] - offset},
        #     'prev_close':
        #         res['meta']['previousClose'],
        #     'trading_period':
        #         [period['start'] - offset, period['end'] - offset],
        #     'price_range':
        #         [min(opens), max(closes)],
        #     'timezone_name':
        #         meta['exchangeTimezoneName']
        # }
        fmt = lambda n: thousands(rounded(n))

        open_quote = fmt(self.on_open['quote'])
        low, high = [fmt(p) for p in self.price_range]
        volume = thousands(self.volume)
        prev_close = fmt(self.prev_close)
        return {
            "Open:": open_quote,
            "Range:": f'{low} – {high}',
            "Volume:": volume,
            "Yesterday's close:": prev_close,
        }

    def to_embed(self, topic):
        try:
            kwargs = {
                attr: getattr(self, attr)
                for attr in (
                    'title',
                    'url',
                    'timestamp',
                    'description',
                    'colour'
                )
            }

            embed = Embed(**kwargs)

            for name, value in self.fields.items():
                embed.add_field(name=name, value=value, inline=True)

            embed.set_footer(text=f'!untrack {topic} to stop these updates')
            return embed

        except Exception as e:
            log.exception(e)
            raise e

    def to_string(self):
        templ = '{sign}  {symbol} {arrow} {price}'
        templ_diff = '   {sign}{diffstr} ({sign}{diff_pct}%)'

        sign, arrow = [
            self.by_direction(*options) for options in [
                ('-', Unicode.DOT, '+'),
                (Unicode.ARROW_DOWN, ' ', Unicode.ARROW_UP)
            ]
        ]

        symbol = self.symbol.upper()

        open_quote = self.on_open['quote']
        close_quote = self.on_close['quote']
        price = thousands(rounded(close_quote))

        diff = self._diff
        if diff:
            diffstr = rounded(abs(diff))
            diff_pct = rounded(abs(diff) / open_quote * 100, places=2)
            templ += templ_diff

        return templ.format(**locals())


    def __repr__(self):
        return f'<TickerToday: {self.cachekey}>'


class YahooFinanceMixin:
    """Mixin to be used with discord.ext.command.Cog"""
    @property
    def symbols(self) -> Mapping[str, str]:
        """e.g. { 'S58.SI': 'SATS Ltd.', 'G3B.SI': 'Nikko AM ETF' }"""
        raise NotImplementedError


    @property
    def update_interval_secs(self) -> int:
        return TRACKER_UPDATE_INTERVAL_MINS * 60


    def is_time_to_update(self, h_hour=20, wiggle_mins=WIGGLE_ROOM_MINS):
        """If wiggle == 5, returns true between [(hour-1)55, (hour)05] inclusive
        Hour should be in the range [0, 23] inclusive.

        Generally wiggle_mins should be less than half of update_interval_secs
        """
        interval = self.update_interval_secs // 60
        wiggle = wiggle_mins or interval // 2 # rounds down, thanks Python!
        sg_now = datetime.utcnow().timestamp() + 8 * 60 * 60  # Time now GMT+8
        sg_now_dt = datetime.fromtimestamp(sg_now)
        wkday, hour, minute = map(int, sg_now_dt.strftime('%w %H %M').split())

        h = h_hour % 24

        if wkday in {6: 'Sat', 7: 'Sun'}:
            return False

        if hour == (h - 1) and minute >= (60 - wiggle):
            # if H-hour is 2000, check if time is >= (2000 - wiggle)
            return True

        if hour == h and minute <= wiggle:
            # If time is <= (2000 + wiggle)
            return True

        return False


    async def handle_parsed(self, apidatas: Mapping[str, dict]) -> None:
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

        updates = {}
        for symbol, apidata in apidatas.items():
            name = self.symbols[symbol]
            ticker = TickerToday(symbol, name, apidata)
            if ticker.cachekey not in CACHED:
                updates[ticker.cachekey] = ticker
                CACHED[ticker.cachekey] = True

        if not updates:
            return

        log.info('%s new ticker updates for topic "%s"', len(updates), topic)

        tickers = updates.values()
        sendargs = [
            dict(content=None, embed=self.compose_summary(tickers))
        ]
        await pscog.push_to_topic(self.topic, sendargs)


    async def do_work(self):
        # No-op if not midnight yet
        if not self.is_time_to_update():
            return True

        log.info(f'Checking "{self.topic}" for ticker updates...')

        apidatas = await self.pull()
        self.filter(apidatas)

        parse_ok = {}

        # Preparse json response by unwrapping and discarding most data
        for symbol, apidata in apidatas.items():
            if not apidata:
                # Detected as malformed by filter()
                continue

            parsed = self.preparse(apidata)
            if parsed:
                parse_ok[symbol] = parsed

        if any(parse_ok):  # any() not needed but nice semantics
            await self.handle_parsed(parse_ok)

        return True


    @staticmethod
    def filter(apidatas: Mapping[str, dict]) -> Mapping[str, dict]:
        """Checks for malformed data and unsets the key in-place on apidatas"""
        for symbol, json in apidatas.items():
            try:
                data = json['chart']['result'][0]
                assert all(k in data
                           for k in 'timestamp indicators meta'.split())

            except (KeyError, IndexError, AssertionError):
                log.error('Bad json response from Yahoo Finance API, symbol=%s',
                    symbol)
                apidatas[symbol] = None  # Unset key, since deleting is slower
                continue


    @staticmethod
    def preparse(apidata):
        def floats(iterable):
            return [x for x in iterable if isinstance(x, float)]

        try:
            res = apidata['chart']['result'][0]
            prices = res['indicators']['quote'][0]
            volumes = prices['volume']
            opens = floats(prices['open'])
            closes = floats(prices['close'])

            times = res['timestamp']

            meta = res['meta']
            period = meta['tradingPeriods'][0][0]
            offset = res['meta']['gmtoffset']

            return {
                'on_open':
                    {'time': times[0] - offset, 'quote': opens[0]},
                'on_close':
                    {'time': times[-1] - offset, 'quote': closes[-1]},
                'prev_close':
                    res['meta']['previousClose'],
                'trading_period':
                    [period['start'] - offset, period['end'] - offset],
                'price_range':
                    [min(opens), max(closes)],
                'timezone_name':
                    meta['exchangeTimezoneName'],
                'volume':
                    sum(v for v in volumes if v),
            }
        except (IndexError, KeyError, ValueError) as e:
            log.error(errorformat(e))
            return None


    async def pull(self) -> Mapping[str, dict]:
        loop = self.bot.loop
        urls = [f'https://query1.finance.yahoo.com/v8/finance/chart/{sym.lower()}'
                for sym in self.symbols]
        headers = {
            # 'Referer': f'https://sg.finance.yahoo.com/quote/{ticker.lower()}/'
        }
        params = {
            'region': 'SG',
            'lang': 'en-SG',
            'includePrePost': 'false',
            'range': '1d',
            'corsDomain': 'sg.finance.yahoo.com',
            '.tsrc': 'finance',
        }

        resps = []
        # awaitable:
        a_reqs = self.batch_get_urls(loop, *urls, headers=headers, params=params)
        for resp in await a_reqs:
            if resp.status == 200:
                resps.append(await resp.json())

        return {symbol: json
                for symbol, json in zip(self.symbols, resps)}


    def compose_summary(self, tickers):
        width = max(len(t.name) for t in tickers)
        rows = []
        for t in tickers:
            name = f'[{t.name}]({t.url})'
            desc = t.to_string()
            rows.append(f'**{name}** ```diff\n{desc}```')
        desc = '\n'.join(rows)
        return Embed(description=desc)
