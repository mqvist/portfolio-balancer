from collections import namedtuple, defaultdict
from decimal import Decimal


Stock = namedtuple('Stock', 'symbol asset_class')
Buy = namedtuple('Buy', 'stock amount')


def Money(value):
    return Decimal(value).quantize(Decimal('0.01'))


def compress_buys(buys):
    buy_dict = defaultdict(int)
    for buy in buys:
        buy_dict[buy.stock] += buy.amount
    return [Buy(stock, amount) for stock, amount in buy_dict.items()]
    
