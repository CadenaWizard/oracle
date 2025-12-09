# Copyright (c) 2025-present Cadena Bitcoin
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

from price_common import PriceInfoSingle

from datetime import datetime, UTC
import json
import requests

DEFAULT_MAX_AGE_SECS: int = 15
MIN_PREF_MAX_AGE_SECS: int = 5

# Get rate price info from Binance, and cache it for a while
# E.g. https://api3.binance.com/api/v3/ticker/price?symbol=BTCEUR
# E.g. https://api.binance.us/api/v3/ticker/price?symbol=BTCUSDT
class BinancePriceSource:
    global_or_us = True
    host = "api3.binance.com"
    url_root = ""
    source_id = "Binance_set_later"
    cache = {}

    def __init__(self, global_or_us: bool):
        self.global_or_us = global_or_us
        if global_or_us:
            self.host = "api3.binance.com"
            self.source_id = "Binance"
        else:
            self.host = "api.binance.us"
            self.source_id = "BinanceUS"
        self.url_root = "https://" + self.host + "/api/v3/ticker/price?symbol="
        self.cache = {}
        print("Binance price source initialized,", self.global_or_us, "host", self.host, "src", self.source_id, "url", self.url_root)

    def get_price_info(self, symbol: str, pref_max_age: float = 0) -> float:
        now = datetime.now(UTC).timestamp()
        if pref_max_age == 0:
            pref_max_age = DEFAULT_MAX_AGE_SECS
        pref_max_age = max(pref_max_age, MIN_PREF_MAX_AGE_SECS)

        # symbol specific processing
        if symbol.upper() == "BTCUSD":
            symbol = "BTCUSDT"
        if symbol.upper() == "BTCEUR":
            if not self.global_or_us:
                # US has no EUR
                return PriceInfoSingle.create_with_error(symbol, now, self.source_id, f"Symbol not supported in this region, {symbol}")
            else:
                symbol = "BTCEUR"

        if symbol in self.cache:
            cached = self.cache[symbol]
            age = now - cached.retrieve_time
            if age < pref_max_age:
                # print("Using cached value", cached["pi"].price, cached)
                return cached
        # Not cached, get it now
        price, error = self.do_get_price(symbol)
        if error:
            pi = PriceInfoSingle.create_with_error(symbol, now, self.source_id, error)
        else:
            # No claimed time from source
            claimed_time = now
            pi = PriceInfoSingle(price, symbol, now, claimed_time, self.source_id)
        # Cache it
        # Note: also cache errored info
        self.cache[symbol] = pi
        # print("Saved value to cache", cached["pi"].price, cached)
        return pi

    def do_get_price(self, symbol: str) -> tuple[float, str | None]:
        try:
            url = self.url_root + symbol
            # print("url", url)
            response = requests.get(url)
            if not response.ok:
                return 0, f"Error getting price, {url}, {response.status_code}"
            jsonData = json.loads(response.content)
            # print(jsonData)
            price = jsonData['price']
            if price is None:
                return 0, f"Missing price"
            return float(price), None
        except Exception as ex:
            return 0, f"Exception getting price, {url}, {ex}"
