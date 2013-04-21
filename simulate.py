from invest import *


class SimulatedStockPricer(StockPricer):
    def __init__(self):
        super(SimulatedStockPricer, self).__init__()


SimulatedStockPricer()

stock1 = Stock('iBoxx Global Inflation-linked', 'DBXH.DE', 'bond')
stock2 = Stock('iBoxx EUR Liquid Corporate', 'D5BG.DE', 'bond')
stock3 = Stock('MSCI World', 'DBXW.DE', 'world')
stock4 = Stock('MSCI Emerging Markets', 'DBX1.DE', 'emerging')

portfolio = Portfolio()
portfolio.add_stock(stock1, 28)
portfolio.add_stock(stock3, 484)
portfolio.add_stock(stock4, 20)

target_allocation = Allocation({'bond': 25, 'world': 70, 'emerging': 5})
stocks_available = [stock2, stock3, stock4]
money_to_invest = Money(700)
money_buffer = Money('34.95')

for i in range(100):
    print 80 * '-'
    print 'Round', i + 1
    portfolio, money_buffer = main(portfolio, target_allocation, money_to_invest, money_buffer,
                                   stocks_available)
