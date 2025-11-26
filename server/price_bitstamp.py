# Copyright (c) 2025-present Cadena Bitcoin
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

from price_common import PriceInfo
from datetime import datetime, UTC
import json
import requests

BITSTAMP_URL_ROOT: str = "https://www.bitstamp.net/api/v2/ticker/"
BITSTAMP_CACHE_FOR_SECS: int = 30

# Get rate price info from Bitstamp, and cache it for a while
# E.g. https://www.bitstamp.net/api/v2/ticker/btceur
class BitstampPriceSource:
    cache = {}

    def __init__(self):
        self.cache = {}

    def get_price_info(self, symbol: str, dummy_time) -> float:
        now = datetime.now(UTC).timestamp()

        # symbol specific processing
        if symbol.upper() == "BTCUSD":
            symbol = "btcusd"
        if symbol.upper() == "BTCEUR":
            symbol = "btceur"

        if symbol in self.cache:
            cached = self.cache[symbol]
            age = now - cached["t"]
            if age < BITSTAMP_CACHE_FOR_SECS:
                # print("Using cached value", cached["pi"].price, cached)
                return cached["pi"]
        # Not cached, get it now
        price = BitstampPriceSource.do_get_price(symbol)
        pi = PriceInfo(price, symbol, now, "Bitstamp")
        # Cache it
        # Note: also cache errored info
        cached = {
            "t": now,
            "pi": pi
        }
        self.cache[symbol] = cached
        # print("Saved value to cache", cached["pi"].price, cached)
        return pi

    def do_get_price(symbol: str) -> float:
        url = BITSTAMP_URL_ROOT + symbol
        # print("url", url)
        response = requests.get(url)
        if (response.ok):
            jsonData = json.loads(response.content)
            price = jsonData['last']
            if price is not None:
                return float(price)
        else:
            print("Error fetching price", url, "error", response)
        return 0
