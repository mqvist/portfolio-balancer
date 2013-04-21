import sys
from collections import defaultdict
from itertools import count
import datetime
import ConfigParser

import stock_pricer
from util import *


class Allocation(object):
    def __init__(self, asset_classes_percents):
        self._asset_classes_percents = dict(asset_classes_percents)
        assert sum(self._asset_classes_percents.values()) == 100

    def __eq__(self, other):
        return self._asset_classes_percents == other._asset_classes_percents

    def __getitem__(self, key):
        return self._asset_classes_percents[key]

    def __iter__(self):
        return iter(self._asset_classes_percents.items())

    @property
    def asset_classes(self):
        return self._asset_classes_percents.keys()
    
    @property
    def percents(self):
        return self._asset_classes_percents.values()


class Portfolio(object):
    def __init__(self):
        self._stocks_amounts = defaultdict(int)
        self._asset_class_values = {}
    
    def __eq__(self, other):
        return self._stocks_amounts == other._stocks_amounts

    def __iter__(self):
        return iter(self._stocks_amounts.items())

    def __str__(self):
        lines = []
        for stock, amount in self:
            price = self._pricer.get_price(stock)
            name = self._pricer.get_name(stock)
            value = price * amount
            lines.append('%-30s: %4d x %6.2f = %10.2f' % (name, amount, price, value))
        lines.append('%-30s: %26.2f' % ('Total value', self.value))
        return '\n'.join(lines)

    @property
    def _pricer(self):
        return stock_pricer.StockPricer.get_pricer()
    
    def clone(self):
        clone = Portfolio()
        for stock, amount in self:
            clone.add_stock(stock, amount)
        return clone

    @property
    def asset_classes(self):
        return set(stock.asset_class for stock in self._stocks_amounts)

    @property
    def value(self):
        return sum(self.asset_class_value(asset_class) for asset_class in self.asset_classes)

    def asset_class_value(self, asset_class):
        if asset_class not in self._asset_class_values:
            value = Money(sum(self._pricer.get_price(stock) * amount for stock, amount in self if stock.asset_class == asset_class))
            self._asset_class_values[asset_class] = value
        return self._asset_class_values[asset_class]

    def add_stock(self, stock, amount):
        if amount < 1:
            return
        self._stocks_amounts[stock] += amount
        self._value = None
        try:
            del self._asset_class_values[stock.asset_class]
        except KeyError:
            pass

    def get_asset_class_percent(self, asset_class):
        p = 100.0 * float(self.asset_class_value(asset_class)) / float(self.value)
        return p

    def print_asset_class_balance(self, target_allocation):
        print 'Asset class  Allocation    Target Deviation'
        for asset_class in self.asset_classes:
            current = self.get_asset_class_percent(asset_class)
            target = target_allocation[asset_class]
            deviation = current - target
            print '%-12s: %8.1f%% %8.1f%% %+8.1f%%' % (asset_class, current, target, deviation)
    

def get_next_buys(portfolio, target_allocation, available_stocks, money, pricer):
    assert money > 0

    buys = []
    
    def get_next_state(portfolio, money_remaining):
        def calculate_state_error(state):
            _, new_portfolio, new_money_remaining = state
            asset_classes = set(new_portfolio.asset_classes) | set(target_allocation.asset_classes)
            error = 0.0
            for asset_class in asset_classes:
                error += abs(new_portfolio.get_asset_class_percent(asset_class) -
                             target_allocation[asset_class])**2
            error += abs(float(new_money_remaining) / float(money))
            return error
        
        def create_state(stock):
            new_portfolio = portfolio.clone()
            new_portfolio.add_stock(stock, 1)
            new_money_remaining = money_remaining - pricer.get_price(stock)
            if new_money_remaining < 0:
                return None
            return Buy(stock, 1), new_portfolio, new_money_remaining

        next_states = filter(None, [create_state(stock) for stock in available_stocks])
        return min(next_states, key=calculate_state_error) if next_states else None

    money_remaining = money
    while 1:
        next_state = get_next_state(portfolio, money_remaining)
        if next_state is None:
            break
        next_buy, portfolio, money_remaining = next_state
        buys.append(next_buy)

    return compress_buys(buys), portfolio, money_remaining


def read_invest_file(inifile):
    portfolio = Portfolio()
    config = ConfigParser.ConfigParser()
    config.optionxform = str
    config.readfp(inifile)
    symbols_stocks = {}
    for symbol, amount in config.items('portfolio'):
        asset_class = config.get(symbol, 'asset_class')
        stock = Stock(symbol, asset_class)
        portfolio.add_stock(stock, int(amount))
    target_allocation = Allocation(dict((a, int(b)) for a, b in config.items('target_allocation')))
    stock_symbols = set(config.sections()) - set(['portfolio', 'target_allocation'])
    available_stocks = []
    for symbol in stock_symbols:
        if config.get(symbol, 'available') == 'yes':
            asset_class = config.get(symbol, 'asset_class')
            available_stocks.append(Stock(symbol, asset_class))
    return portfolio, target_allocation, available_stocks


def main(portfolio, target_allocation, stocks_available, money_to_invest):
    pricer = stock_pricer.StockPricer.get_pricer()
    print 'Current portfolio'
    print(portfolio)
    print 'Current asset class balance'
    portfolio.print_asset_class_balance(target_allocation)
    print 'Finding investment actions'
    buys, new_portfolio, money_remaining = get_next_buys(portfolio, target_allocation, stocks_available,
                                                     money_to_invest, pricer)
    money_spent = money_to_invest - money_remaining
    print 'Found actions'
    for stock, amount in buys:
        price = pricer.get_price(stock)
        total_price = amount * price
        percent = 100.0 * float(total_price) / float(money_spent)
        print ' - Buy %3d x %-30s for %7.2f (%2.0f%%)' % (amount, stock.symbol, total_price, percent)
    print 'Money spent %.2f, remaining %.2f' % (money_spent, money_remaining)
    print 'New portfolio'
    print(new_portfolio)
    print 'New asset class balance'
    new_portfolio.print_asset_class_balance(target_allocation)
    return new_portfolio, money_remaining


if __name__ == '__main__':
    portfolio, target_allocation, available_stocks = read_invest_file(open(sys.argv[1]))
    money_to_invest = Money(sys.argv[2])
    pricer = stock_pricer.YahooStockPricer()
    stock_pricer.StockPricer.set_pricer(pricer)

    print 'Investing %.2f' % money_to_invest
    portfolio, money_remaining = main(portfolio, target_allocation, available_stocks, money_to_invest)

        
