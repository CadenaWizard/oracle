# Copyright (c) 2025-present Cadena Bitcoin
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

from price_common import PriceInfoSingle

from datetime import datetime, UTC
import json
import requests

BINANCE_CACHE_FOR_SECS: int = 15

# Get rate price info from Binance, and cache it for a while
# E.g. https://api3.binance.com/api/v3/ticker/price?symbol=BTCEUR
# E.g. https://api.binance.us/api/v3/ticker/price?symbol=BTCUSDT
class BinancePriceSource:
    global_or_us = True
    host = "api3.binance.com"
    url_root = ""
    source: "Binance"
    cache = {}

    def __init__(self, global_or_us: bool):
        self.global_or_us = global_or_us
        if global_or_us:
            self.host = "api3.binance.com"
            self.source = "Binance"
        else:
            self.host = "api.binance.us"
            self.source = "BinanceUS"
        self.url_root = "https://" + self.host + "/api/v3/ticker/price?symbol="
        self.cache = {}
        print("Binance price source initialized,", self.global_or_us, "host", self.host, "src", self.source, "url", self.url_root)

    def get_price_info(self, symbol: str, dummy_time) -> float:
        now = datetime.now(UTC).timestamp()

        # symbol specific processing
        if symbol.upper() == "BTCUSD":
            symbol = "BTCUSDT"
        if symbol.upper() == "BTCEUR":
            if not self.global_or_us:
                # US has no EUR
                return PriceInfoSingle.create_with_error(symbol, now, self.source, f"Symbol not supported in this region, {symbol}")
            else:
                symbol = "BTCEUR"

        if symbol in self.cache:
            cached = self.cache[symbol]
            age = now - cached.retrieve_time
            if age < BINANCE_CACHE_FOR_SECS:
                # print("Using cached value", cached["pi"].price, cached)
                return cached
        # Not cached, get it now
        price = self.do_get_price(symbol)
        pi = PriceInfoSingle(price, symbol, now, self.source)
        # Cache it
        # Note: also cache errored info
        self.cache[symbol] = pi
        # print("Saved value to cache", cached["pi"].price, cached)
        return pi

    def do_get_price(self, symbol: str) -> float:
        url = self.url_root + symbol
        # print("url", url)
        response = requests.get(url)
        if (response.ok):
            jsonData = json.loads(response.content)
            price = jsonData['price']
            if price is not None:
                return float(price)
        else:
            print("Error fetching price", url, "error", response)
        return 0
