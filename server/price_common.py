# Copyright (c) 2025-present Cadena Bitcoin
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

class PriceInfo:
    """
    Represents a single price data.
    @param price: float -- The price value
    @param symbol: str -- The symbol, e.g. "BTCUSD". All/uppercase recommended.
    @param retrieve_time: float -- The time of retrieval
    @param source: str -- The internal ID of the source, e.g. "Binance"
    """
    def __init__(self, price: float, symbol: str, retrieve_time: float, source: str):
        self.price = price
        self.symbol = symbol
        self.retrieve_time = retrieve_time
        self.source = source

