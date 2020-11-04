from datetime import datetime
from pprint import pprint as pp

import requests

URL = '''https://query1.finance.yahoo.com/v8/finance/chart/{ticker}'''

datestr = lambda ts: datetime.fromtimestamp(ts).strftime('%d-%b-%Y %H:%M GMT+8')
imin = lambda iterables: min(floats(iterables))
imax = lambda iterables: max(floats(iterables))

def floats(iterable):
    return filter(lambda i: isinstance(i, float), iterable)

def rounded(n, places=4):
    s = '{:0%df}' % places
    return float(s.format(n))


def pull(ticker, time_range):
    valid_time_ranges = [
        '1d', '5d',
        '1mo', '3mo', '6mo',
        '1y', '2y', '5y', '10y',
        'ytd'
    ]
    if time_range not in valid_time_ranges:
        time_range = valid_time_ranges[0]

    query_params = dict(
        region='SG',
        lang='en-SG',
        includePrePost='false',
        range=time_range,
        corsDomain='sg.finance.yahoo.com'
    )
    query_params['.tsrc'] = 'finance'

    headers = {
        'Referer': f'https://sg.finance.yahoo.com/quote/{ticker.lower()}/'
    }

    res = requests.get(URL.format(ticker=ticker.upper()))
    if res.ok:
        return res.json()['chart']['result'][0]
    else:
        msg = f'{res.status_code}: {res.text}'
        raise RuntimeError(msg)


def get_prices(ticker, time_range=None):
    res = pull(ticker, time_range)
    
    times = res['timestamp']
    prices = res['indicators']['quote'][0]
    meta = res['meta']
    tradingPeriods = meta['tradingPeriods'][0][0]

    return {
        'on_open':
                {'time': datestr(times[0]), 'quote': rounded(prices['open'][0])},
        'on_close':
                {'time': datestr(times[-1]), 'quote': rounded(prices['close'][-1])},
        'prev_close':
                res['meta']['previousClose'],
        'trading_period':
                (datestr(tradingPeriods['start']), datestr(tradingPeriods['end'])),
        'price_range':
                (rounded(imin(prices['close'])), rounded(imax(prices['close']))),
    }

x = get_prices('s58.si')
