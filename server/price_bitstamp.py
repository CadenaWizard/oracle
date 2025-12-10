# Copyright (c) 2025-present Cadena Bitcoin
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

from price_common import PriceInfoSingle

from datetime import datetime, UTC
import requests

BITSTAMP_URL_ROOT: str = "https://www.bitstamp.net/api/v2/ticker/"
DEFAULT_MAX_AGE_SECS: int = 15
MIN_PREF_MAX_AGE_SECS: int = 5

# Get rate price info from Bitstamp, and cache it for a while
# E.g. https://www.bitstamp.net/api/v2/ticker/btceur
class BitstampPriceSource:
    def __init__(self):
        self.source_id = "Bitstamp"
        self.cache = {}

    def get_source_id(self):
        return self.source_id

    def process_symbol(self, symbol) -> str | None:
        if symbol.upper() == "BTCUSD":
            return "btcusd"
        if symbol.upper() == "BTCEUR":
            return "btceur"
        return None

    def get_price_info_fast(self, symbol: str, pref_max_age: float = 0) -> float | None:
        now = datetime.now(UTC).timestamp()

        symbol = self.process_symbol(symbol)
        if not symbol:
            return PriceInfoSingle.create_with_error(symbol, now, self.source_id, f"Symbol not supported (in this region), {symbol}")

        if pref_max_age == 0:
            pref_max_age = DEFAULT_MAX_AGE_SECS
        pref_max_age = max(pref_max_age, MIN_PREF_MAX_AGE_SECS)

        if symbol in self.cache:
            cached = self.cache[symbol]
            age = now - cached.retrieve_time
            if age < pref_max_age:
                # print("Using cached value", cached["pi"].price, cached)
                return cached

        # Not cached
        return None

    def get_price_info(self, symbol: str, pref_max_age: float = 0) -> float:
        now = datetime.now(UTC).timestamp()

        fast = self.get_price_info_fast(symbol, pref_max_age)
        if fast is not None:
            return fast

        symbol = self.process_symbol(symbol)
        if not symbol:
            return PriceInfoSingle.create_with_error(symbol, now, self.source_id, f"Symbol not supported (in this region), {symbol}")

        # Get price now
        price, claimed_time, error = BitstampPriceSource.do_get_price(symbol)
        if error:
            pi = PriceInfoSingle.create_with_error(symbol, now, self.source_id, error)
        else:
            pi = PriceInfoSingle(price, symbol, now, claimed_time, self.source_id)
        # Cache it
        # Note: also cache errored info
        self.cache[symbol] = pi
        # print("Saved value to cache", cached["pi"].price, cached)
        return pi

    def do_get_price(symbol: str) -> tuple[float, float, str | None]:
        try:
            url = BITSTAMP_URL_ROOT + symbol
            # print("url", url)
            response = requests.get(url)
            if not response.ok:
                return 0, 0, f"Error getting price, {url}, {response.status_code}"
            jsonData = response.json()
            # print(jsonData)
            price = jsonData['last']
            if price is None:
                return 0, 0, f"Missing price"
            claimed_time = jsonData['timestamp']
            return float(price), float(claimed_time), None
        except Exception as ex:
            return 0, 0, f"Exception getting price, {url}, {ex}"
