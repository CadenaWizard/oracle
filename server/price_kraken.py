# Copyright (c) 2025-present Cadena Bitcoin
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

from price_common import PriceInfoSingle

from datetime import datetime, UTC
import requests

DEFAULT_MAX_AGE_SECS: int = 15
MIN_PREF_MAX_AGE_SECS: int = 5

# Get rate price info from Kraken, and cache it for a while
# See https://docs.kraken.com/api/docs/rest-api/get-ticker-information
# E.g. curl 'https://api.kraken.com/0/public/Ticker?pair=XBTUSD' -H 'Accept: application/json'
class KrakenPriceSource:
    def __init__(self):
        self.host = "api.kraken.com"
        self.source_id = "Kraken"
        self.url_root = f"https://{self.host}/0/public/Ticker?pair="
        self.cache = {}
        print(f"Kraken price source initialized, host {self.host}, src {self.source_id}, url {self.url_root}")

    def get_source_id(self):
        return self.source_id

    def get_price_info_fast(self, symbol: str, pref_max_age: float = 0) -> float | None:
        now = datetime.now(UTC).timestamp()

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

        # Get price now
        price, error = self.do_get_price(symbol)
        if error:
            pi = PriceInfoSingle.create_with_error(symbol, now, self.source_id, error)
        else:
            # No claimed time from source
            pi = PriceInfoSingle(price, symbol, now, 0, self.source_id)
        # Cache it
        # Note: also cache errored info
        self.cache[symbol] = pi
        # print("Saved value to cache", cached["pi"].price, cached)
        return pi

    def internal_symbol(self, symbol) -> tuple[str, str]:
        symbol = symbol.upper()
        if symbol == "BTCUSD":
            return ("XBTUSD", "XXBTZUSD")
        if symbol == "BTCEUR":
            return ("XBTEUR", "XXBTZEUR")
        return (None, None)

    def do_get_price(self, symbol: str) -> tuple[float, str | None]:
        try:
            symb_int1, symb_int2 = self.internal_symbol(symbol)
            if symb_int1 is None or symb_int2 is None:
                return 0, f"Symbol is not supported, {symbol}"
            url = self.url_root + symb_int1
            # print("url", url)
            response = requests.get(url)
            if not response.ok:
                return 0, f"Error getting price, {url}, {response.status_code}"
            jsonData = response.json()
            # print(jsonData)
            result = jsonData["result"]
            if result is not None:
                symbinfo = result[symb_int2]
                if symbinfo is not None:
                    lasttrade = symbinfo["c"]
                    if lasttrade is not None:
                        value = float(lasttrade[0])
                        if value is not None:
                            return value, None
            return 0, f"Error parsing price, {url}, {jsonData}"
        except Exception as ex:
            return 0, f"Exception getting price, {url}, {ex}"
