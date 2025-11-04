class PriceInfo:
    def __init__(self, price, symbol, time, source):
        self.price = price
        self.symbol = symbol
        self.time = time
        self.source = source

    price: float
    symbol: str
    time: float
    source: str
