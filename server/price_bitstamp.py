# Copyright (c) 2025-present Cadena Bitcoin
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

from price_common import PriceInfoSingle
from datetime import datetime, UTC
import json
import requests

BITSTAMP_URL_ROOT: str = "https://www.bitstamp.net/api/v2/ticker/"
BITSTAMP_CACHE_FOR_SECS: int = 15

# Get rate price info from Bitstamp, and cache it for a while
# E.g. https://www.bitstamp.net/api/v2/ticker/btceur
class BitstampPriceSource:
    cache = {}
    source_id = "Bitstamp"

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
            age = now - cached.retrieve_time
            if age < BITSTAMP_CACHE_FOR_SECS:
                # print("Using cached value", cached["pi"].price, cached)
                return cached
        # Not cached, get it now
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
            jsonData = json.loads(response.content)
            # print(jsonData)
            price = jsonData['last']
            if price is None:
                return 0, 0, f"Missing price"
            claimed_time = jsonData['timestamp']
            return float(price), float(claimed_time), None
        except Exception as ex:
            return 0, 0, f"Exception getting price, {url}, {ex}"
