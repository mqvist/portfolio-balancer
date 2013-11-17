import datetime
import unittest
import StringIO

from mock import Mock, sentinel, call, patch

from seligson import *


def make_portfolio_file(allocations=[30, 50, 20]):
    return StringIO.StringIO('''[Eurooppa]
omistus=5.000
allokaatio={0}
[Pohjois-Amer.]
omistus=60.000
allokaatio={1}
palkkio_prosentti=0.1
[Aasia]
omistus=20.000
allokaatio={2}'''.format(*allocations))


def make_pricer():
    return MockPricer({'Eurooppa': SharePrice('2'),
                       'Pohjois-Amer.': SharePrice('0.5'),
                       'Aasia': SharePrice('1')})


def make_portfolio():
    return read_portfolio(make_portfolio_file())


class MockPricer(object):
    def __init__(self, price_map):
        self.price_map = price_map
    
    def get_share_price(self, fund_name):
        return self.price_map[fund_name]


class AcceptanceTest(unittest.TestCase):
    @patch('urllib.urlopen')
    def test(self, urlopen):
        html = open('fundvalues.html').read()
        urlopen.return_value.read.return_value = html
        
        portfolio = make_portfolio()
        main(portfolio, Money(100))
    

class MainTest(unittest.TestCase):
    def test(self):
        investment_strategy = Mock(return_value=(sentinel.investments, sentinel.new_portfolio))
        pricer = sentinel.pricer
        printer = Mock()
        
        main(sentinel.portfolio, sentinel.amount, pricer, investment_strategy, printer)

        printer.print_current_portfolio.assert_called_once_with(sentinel.portfolio,
                                                                sentinel.pricer)
        investment_strategy.assert_called_once_with(sentinel.portfolio, sentinel.amount,
                                                    sentinel.pricer, Money(50))
        printer.print_investments.assert_called_once_with(sentinel.investments)
        printer.print_new_portfolio.assert_called_once_with(sentinel.new_portfolio,
                                                            sentinel.pricer)


class PrinterTest(unittest.TestCase):
    def setUp(self):
        self.output = StringIO.StringIO()
        self.printer = Printer(self.output)
    
    def test_print_current_portfolio(self):
        portfolio = make_portfolio()
        
        self.printer.print_current_portfolio(portfolio, make_pricer())
        
        expected_output = '''Seligson rahastot {0}
Rahasto                 Arvo   Osuus Tavoite     Ero
----------------------------------------------------
Aasia                  20.00   33.3%   20.0%  +13.3%
Eurooppa               10.00   16.7%   30.0%  -13.3%
Pohjois-Amer.          30.00   50.0%   50.0%   +0.0%
----------------------------------------------------
Yht.                   60.00                        
'''.format(datetime.date.today())

        self.assertMultiLineEqual(expected_output, self.output.getvalue())

    def test_print_investments(self):
        fund1 = Mock()
        fund1.name = 'Fund1'
        fund1.calculate_fee.return_value = Money(0)
        fund2 = Mock()
        fund2.name = 'Fund2'
        fund2.calculate_fee.return_value = Money(0.2)
        investments = [Investment(fund1, Money(10)),
                       Investment(fund2, Money(20))]
        
        self.printer.print_investments(investments)

        expected_output = '''Sijoitukset:
Rahasto                Summa Palkkio Rahastoon
----------------------------------------------
Fund1                  10.00    0.00     10.00
Fund2                  20.00    0.20     19.80
----------------------------------------------
Yht.                   30.00    0.20     29.80
'''.format(datetime.date.today())
        
        self.assertMultiLineEqual(expected_output, self.output.getvalue())


class ReadFundConfigTest(unittest.TestCase):
    def test(self):
        portfolio = read_portfolio(make_portfolio_file())
        self.assertEqual(3, len(portfolio.funds))
        self.assertEqual([Fund('Aasia', ShareAmount(20), Allocation(20)),
                          Fund('Eurooppa', ShareAmount(5), Allocation(30)),
                          Fund('Pohjois-Amer.', ShareAmount(60), Allocation(50))],
                         portfolio.funds)
        
    def test_invalid_allocations(self):
        invalid_portfolio_file = make_portfolio_file([10, 20, 30])
        self.assertRaises(ValueError, read_portfolio, invalid_portfolio_file)
        
    
class PricerTest(unittest.TestCase):
    def test_existing_share(self):
        html = open('fundvalues.html').read()
        mock_downloader = Mock(return_value=html)
        pricer = Pricer(mock_downloader)
        self.assertEqual(SharePrice('2.1363'), pricer.get_share_price('Eurooppa'))


class CalculateInvestmentsTest(unittest.TestCase):
    def setUp(self):
        self.portfolio = make_portfolio()
        self.asia_fund = self.portfolio.funds[0]
        self.euro_fund = self.portfolio.funds[1]
        self.usa_fund = self.portfolio.funds[2]
        self.pricer = make_pricer()
    
    def test_balanced_investments_(self):
        investments, new_portfolio = calculate_investments(self.portfolio, Money(100),
                                                           self.pricer, 0)

        self.assertEqual([Investment(self.asia_fund, Money(12)),
                          Investment(self.euro_fund, Money(38)),
                          Investment(self.usa_fund, Money(50))],
                         investments)

    def test_unbalanced_investments_(self):
        investments, new_portfolio = calculate_investments(self.portfolio, Money(10),
                                                           self.pricer, 0)

        self.assertEqual([Investment(self.euro_fund, Money(8)),
                          Investment(self.usa_fund, Money(2))], investments)

    def test_new_portfolio(self):
        investments, new_portfolio = calculate_investments(self.portfolio, Money(100),
                                                           self.pricer, 0)

        self.assertEqual([Fund('Aasia', ShareAmount(32), Allocation(20)),
                          Fund('Eurooppa', ShareAmount(24), Allocation(30)),
                          Fund('Pohjois-Amer.', ShareAmount(159.9), Allocation(50))],
                         new_portfolio.funds)

        
if __name__ == '__main__':
    unittest.main()
