# coding=utf-8
import sys
from decimal import Decimal
import datetime
import ConfigParser
import urllib
from collections import namedtuple

from bs4 import BeautifulSoup


def Money(value):
    return Decimal(value).quantize(Decimal('0.01'))


def ShareAmount(value):
    return Decimal(value).quantize(Decimal('0.0001'))


def SharePrice(value):
    return Decimal(value).quantize(Decimal('0.0001'))


def Allocation(value):
    return Decimal(value).quantize(Decimal('0.1'))


def FeePercent(value):
    return Decimal(value).quantize(Decimal('0.1'))


class Portfolio(object):
    def __init__(self):
        self.funds = []

    def new_with_investments(self, investments, pricer):
        portfolio = Portfolio()
        investment_map = dict((i.fund.name, i.real_investment) for i in investments)
        for fund in self.funds:
            if fund.name in investment_map:
                share_price = pricer.get_share_price(fund.name)
                new_shares = investment_map[fund.name] / share_price
                fund.shares += new_shares
            portfolio.add_fund(fund)
        return portfolio

    def calculate_value(self, pricer):
        return sum(fund.calculate_value(pricer) for fund in self.funds)

    def add_fund(self, fund):
        self.funds.append(fund)
        

class Fund(object):
    def __init__(self, name, shares, target_allocation, fee_percent=0.0):
        self.name = name.decode('utf-8')
        self.shares = ShareAmount(shares)
        self.target_allocation = Allocation(target_allocation)
        self.fee_percent = FeePercent(fee_percent)

    def __repr__(self):
        return 'Fund({0}, {1}, {2})'.format(repr(self.name), repr(self.shares), repr(self.target_allocation))

    def __eq__(self, other):
        return self.name == other.name and self.shares == other.shares and self.target_allocation == other.target_allocation

    def calculate_value(self, pricer):
        return Money(self.shares * pricer.get_share_price(self.name))

    def calculate_fee(self, amount):
        return Money(amount * self.fee_percent / 100)
    

class Investment(object):
    def __init__(self, fund, amount):
        self.fund = fund
        self.amount = amount

    def __eq__(self, other):
        return self.fund == other.fund and self.amount == other.amount

    @property
    def fee(self):
        return self.fund.calculate_fee(self.amount)

    @property
    def real_investment(self):
        return self.amount - self.fee

    
def format_fund_line(*fields):
    return u'{0:20}{1:>8}{2:>8}{3:>8}{4:>8}'.format(*fields)


def make_separator_line():
    return '-' * (20+4*8)


def make_header_lines(header):
    return [header,
            format_fund_line('Rahasto', 'Arvo', 'Osuus', 'Tavoite', 'Ero'),
            make_separator_line()]


def read_portfolio(portfolio_file):
    portfolio = Portfolio()
    
    config = ConfigParser.ConfigParser()
    config.optionxform = str
    config.readfp(portfolio_file)
    
    for fund_name in sorted(config.sections()):
        value = config.get(fund_name, 'omistus')
        shares = ShareAmount(value.replace(',', '.'))
        target_allocation = Allocation(config.get(fund_name, 'allokaatio'))
        if config.has_option(fund_name, 'palkkio_prosentti'):
            fee_percent = FeePercent(config.get(fund_name, 'palkkio_prosentti'))
        else:
            fee_percent = FeePercent(0)
        portfolio.add_fund(Fund(fund_name, shares, target_allocation, fee_percent))

    total_allocation = sum(fund.target_allocation for fund in portfolio.funds)
    if total_allocation != 100:
        raise ValueError('Portfolio fund allocations sum to %d%% != 100%%' % total_allocation)
        
    return portfolio
    

def adjust_investments(investments, target_amount):
    while 1:
        total_investment = sum(i.amount for i in investments)
        excess = total_investment - target_amount
        n = len(investments)
        per_investment_excess = excess / n
        investments = [i for i in investments if i.amount >= per_investment_excess]
        if len(investments) == n:
            break
    return [Investment(i.fund, Money(round(i.amount - per_investment_excess))) for i in investments]


def filter_too_low_investments(investments, min_investment_amount=0):
    valid_investments = []
    for investment in investments:
        if investment.amount < min_investment_amount:
            print u'! Rahasto {0} jää alle minimisijoituksen ({1}€ < {2}€)'.format(investment.fund.name, investment.amount, min_investment_amount).encode('utf-8')
            continue
        valid_investments.append(investment)
    return valid_investments


def calculate_investments(portfolio, target_amount, pricer, min_investment_amount=0):
    assert target_amount > 0
    
    portfolio_value = portfolio.calculate_value(pricer)
    new_value = portfolio_value + target_amount
    investments = [Investment(fund, Money(fund.target_allocation / 100 * new_value - fund.calculate_value(pricer))) for fund in portfolio.funds]
    
    investments = adjust_investments(investments, target_amount)
    if min_investment_amount > 0:
        investments = filter_too_low_investments(investments, min_investment_amount)
        investments = adjust_investments(investments, target_amount)
        
    new_portfolio = portfolio.new_with_investments(investments, pricer)
        
    return investments, new_portfolio


class Printer(object):
    def __init__(self, output=sys.stdout):
        self.output = output
    
    def _print_portfolio(self, portfolio, pricer, header):
        output_lines = make_header_lines(header)
        portfolio_value = portfolio.calculate_value(pricer)
        for fund in portfolio.funds:
            fund_value = fund.calculate_value(pricer)
            if portfolio_value > 0.0:
                actual_allocation = fund_value / portfolio_value * 100
            else:
                actual_allocation = 0
            actual_str = '{0:.1f}%'.format(actual_allocation)
            target_str = '{0:.1f}%'.format(fund.target_allocation)
            deviation_str = '{0:+.1f}%'.format(actual_allocation - fund.target_allocation)
            output_lines.append(format_fund_line(fund.name, fund_value, actual_str, target_str,
                                                 deviation_str))
        output_lines.append(make_separator_line())
        output_lines.append(format_fund_line(u'Yhteensä', portfolio_value, '', '', ''))
        print >>self.output, '\n'.join(output_lines).encode('utf-8')

    def print_current_portfolio(self, portfolio, pricer):
        self._print_portfolio(portfolio, pricer, 'Seligson rahastot %s' % datetime.date.today())

    def print_new_portfolio(self, portfolio, pricer):
        self._print_portfolio(portfolio, pricer, 'Uusi portfolio')
        
    def print_investments(self, investments):
        def format_line(*args):
            return u'{0:20}{1:>8}{2:>8}{3:>10}'.format(*args)
        
        output_lines = ['Sijoitukset:',
                        format_line('Rahasto', 'Summa', 'Palkkio', 'Rahastoon'),
                        '-' * 46]
        total_amount = Money(0)
        total_fees = Money(0)
        total_investment = Money(0)
        for investment in investments:
            output_lines.append(format_line(investment.fund.name, investment.amount, investment.fee, investment.real_investment))
            total_amount += investment.amount
            total_fees += investment.fee
            total_investment += investment.real_investment
            
        output_lines.append('-' * 46)
        output_lines.append(format_line(u'Yhteensä', total_amount, total_fees, total_investment))
        
        print >>self.output, '\n'.join(output_lines).encode('utf-8')
        
        
def seligson_downloader():
    return urllib.urlopen('http://www.seligson.fi/suomi/rahastot/FundValues_FI.html').read()


class Pricer(object):
    def __init__(self, downloader=seligson_downloader):
        self.downloader = downloader
        self._soup = None

    def _get_soup(self):
        if self._soup is None:
            html = self.downloader()
            self._soup = BeautifulSoup(html)
        return self._soup
        
    def get_share_price(self, share_name):
        value = self._get_soup().find('a', text=share_name).parent.parent('td')[2].text
        return SharePrice(value.replace(',', '.'))


def main(portfolio, amount, minimum_investment=None, pricer=Pricer(),
         investment_strategy=calculate_investments, printer=Printer()):
    printer.print_current_portfolio(portfolio, pricer)
    investments, new_portfolio = investment_strategy(portfolio, amount, pricer,
                                                     minimum_investment)
    printer.print_investments(investments)
    printer.print_new_portfolio(new_portfolio, pricer)


if __name__ == '__main__':
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument('portfolio')
    parser.add_argument('amount')
    parser.add_argument('-m', '--minimum-investment', help='minimum investment',
                        type=Money)
    args = parser.parse_args()
    
    portfolio = read_portfolio(open(args.portfolio))
    amount = Money(args.amount)
    main(portfolio, amount, args.minimum_investment)
