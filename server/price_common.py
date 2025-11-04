# Copyright (c) 2025-present Cadena Bitcoin
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

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
