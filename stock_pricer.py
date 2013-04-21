import urllib
import re

from util import Money


class StockPricer(object):
    _instance = None

    @classmethod
    def set_pricer(cls, pricer):
        cls._instance = pricer

    @classmethod
    def get_pricer(cls):
        return cls._instance

    
class YahooStockPricer(StockPricer):
    def __init__(self):
        self._cache = {}

    @staticmethod
    def parse_yahoo_stock_price(html):
        m = re.search('<span class="time_rtq_ticker"><span id=".*?">(\d+.\d+)</span>', html)
        return Money(m.group(1))

    @staticmethod
    def parse_yahoo_stock_name(html):
        m = re.search('<div class="title"><h2>(.*?) \(.*\)</h2>', html)
        return m.group(1)

    def _cache_stock(self, stock):
        url = 'http://finance.yahoo.com/q?s=' + stock.symbol
        html = urllib.urlopen(url).read()
        name = self.parse_yahoo_stock_name(html)
        price = self.parse_yahoo_stock_price(html)
        self._cache[stock.symbol] = (name, price)

    def get_price(self, stock):
        if stock.symbol not in self._cache:
            self._cache_stock(stock)
        return self._cache[stock.symbol][1]

    def get_name(self, stock):
        if stock.symbol not in self._cache:
            self._cache_stock(stock)
        return self._cache[stock.symbol][0]
    
