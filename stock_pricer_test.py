import unittest

from mock import Mock, sentinel

from util import *
from stock_pricer import *


class ParseYahooPriceTest(unittest.TestCase):
    def test_get_price(self):
        html = open('yahoo.html').read()
        self.assertEqual(Money(27.64), YahooStockPricer.parse_yahoo_stock_price(html))
        
    def test_get_name(self):
        html = open('yahoo.html').read()
        self.assertEqual('DBXT MSCI WORLD 1C', YahooStockPricer.parse_yahoo_stock_name(html))
