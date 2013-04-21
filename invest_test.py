import os
import unittest
import datetime
import tempfile
from cStringIO import StringIO
from mock import Mock, sentinel, call, patch

from stock_pricer import StockPricer
from util import Money
from invest import *


stock1 = Stock('SYM1', 'bond')
stock2 = Stock('SYM2', 'bond')
stock3 = Stock('SYM3', 'world')
stock4 = Stock('SYM4', 'emerging')


class FakePricer(StockPricer):
    def __init__(self):
        self.price_dict = {stock1: Money(4), stock2: Money(10), stock3: Money(3),
                           stock4: Money(7)}
    
    def get_price(self, stock):
        return self.price_dict[stock]

    def get_name(self, stock):
        return stock.symbol

class TestCaseWithPortfolio(unittest.TestCase):
    def setUp(self):
        self.pricer = FakePricer()
        StockPricer.set_pricer(self.pricer)
        self.portfolio = Portfolio()
        self.portfolio.add_stock(stock1, 10)
        self.portfolio.add_stock(stock2, 2)
        self.portfolio.add_stock(stock3, 100)
        self.target_allocation = Allocation({'bond': 20, 'world': 70, 'emerging': 10})
        self.available_stocks = [stock2, stock3, stock4]
        

class AcceptanceTest(unittest.TestCase):
    def setUp(self):
        StockPricer.set_pricer(FakePricer())
        handle, self.portfolio_path = tempfile.mkstemp()
        open(self.portfolio_path, 'w').write('''[portfolio]
SYM1=10
SYM2=2
SYM3=100
[target_allocation]
bond=20
world=70
emerging=10
[SYM1]
asset_class=bond
available=no
[SYM2]
asset_class=bond
available=yes
[SYM3]
asset_class=world
available=yes
[SYM4]
asset_class=emerging
available=yes''')
    
        self.expected_portfolio = Portfolio()
        self.expected_portfolio.add_stock(stock1, 10)
        self.expected_portfolio.add_stock(stock2, 4)
        self.expected_portfolio.add_stock(stock3, 100)
        self.expected_portfolio.add_stock(stock4, 4)

    def tearDown(self):
        os.remove(self.portfolio_path)

    def test_saved_portfolio(self):
        portfolio, target_allocation, available_stocks = read_invest_file(open(self.portfolio_path))
        new_portfolio, money_remaining = main(portfolio, target_allocation, available_stocks, Money(50))
        self.assertEqual(self.expected_portfolio, new_portfolio)
        self.assertEqual(Money(2), money_remaining)


class MainTest(TestCaseWithPortfolio):
    def setUp(self):
        super(MainTest, self).setUp()
        self.new_portfolio, self.money_remaining = main(
            self.portfolio, self.target_allocation, self.available_stocks, Money(50))

    
    def test_returned_portfolio(self):
        expected_portfolio = Portfolio()
        expected_portfolio.add_stock(stock1, 10)
        expected_portfolio.add_stock(stock2, 4)
        expected_portfolio.add_stock(stock3, 100)
        expected_portfolio.add_stock(stock4, 4)
        self.assertEqual(expected_portfolio, self.new_portfolio)

    def test_remaining_money(self):
        self.assertEqual(Money(2), self.money_remaining)

        
class GetNextBuysTest(TestCaseWithPortfolio):
    def test(self):
        portfolio = Portfolio()
        portfolio.add_stock(stock1, 10)
        portfolio.add_stock(stock2, 2)
        portfolio.add_stock(stock3, 100)
        target_allocation = Allocation({'bond': 20, 'world': 70, 'emerging': 10})
        available_stocks = [stock2, stock3, stock4]
        
        buys, new_portfolio, money_remaining = get_next_buys(
            portfolio, target_allocation, available_stocks, Money(50), self.pricer)

        self.assertItemsEqual([Buy(stock2, 2), Buy(stock4, 4)], buys)
        self.assertEqual(Money(2), money_remaining)
        

class ReadInvestFileTest(unittest.TestCase):
    def setUp(self):
        invest_file = StringIO('''[portfolio]
SYM1=2
SYM3=10
[target_allocation]
bond=30
world=70
[SYM1]
asset_class=bond
available=yes
[SYM2]
asset_class=bond
available=yes
[SYM3]
asset_class=world
available=no''')
        
        self.portfolio, self.target_allocation, self.available_stocks = read_invest_file(invest_file)

    def test_portfolio(self):
        expected_portfolio = Portfolio()
        expected_portfolio.add_stock(stock1, 2)
        expected_portfolio.add_stock(stock3, 10)
        self.assertEqual(expected_portfolio, self.portfolio)
        
    def test_target_allocation(self):
        self.assertEqual(Allocation({'bond': 30, 'world': 70}), self.target_allocation)

    def test_available_stocks(self):
        expected = [Stock('SYM1', 'bond'), Stock('SYM2', 'bond')]
        self.assertItemsEqual(expected, self.available_stocks)
        
if __name__ == '__main__':
    unittest.main()
