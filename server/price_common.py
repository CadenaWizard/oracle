# Copyright (c) 2025-present Cadena Bitcoin
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

class PriceInfoSingle:
    """
    Represents a single price data from a single source
    @param price: float -- The price value
    @param symbol: str -- The symbol, e.g. "BTCUSD". All/uppercase recommended.
    @param retrieve_time: float -- The time of retrieval
    @param source: str -- The internal ID of the source, e.g. "Binance"
    @param error: str -- Only set in case of error. Value should be 0 in that case.
    """
    def __init__(self, price: float, symbol: str, retrieve_time: float, source: str, error: str | None = None):
        self.price = price
        self.symbol = symbol
        self.retrieve_time = retrieve_time
        self.source = source
        self.error = error

    def create_with_error(symbol: str, retrieve_time: float, source: str, error: str):
        return PriceInfoSingle(0, symbol, retrieve_time, source, error)


class PriceInfo:
    """
    Represents a single price data that can be an aggregate.
    @param price: float -- The price value
    @param symbol: str -- The symbol, e.g. "BTCUSD". All/uppercase recommended.
    @param retrieve_time: float -- The time of retrieval
    @param source: str -- The internal ID of the source, e.g. "Binance"
    @param error: str -- Only set in case of error. Value should be 0 in that case.
    @param aggr_sources: list[PriceInfo] - In case of aggregate price, the individual sources.
    """
    def __init__(self, price: float, symbol: str, retrieve_time: float, source: str, aggr_sources: list[PriceInfoSingle] = [], error: str | None = None):
        self.price = price
        self.symbol = symbol
        self.retrieve_time = retrieve_time
        self.source = source
        self.error = error
        self.aggr_sources = aggr_sources

    def create_with_error(symbol: str, retrieve_time: float, source: str, error: str, aggr_sources = []):
        return PriceInfo(0, symbol, retrieve_time, source, aggr_sources, error)

