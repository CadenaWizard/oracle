# Copyright (c) 2025-present Cadena Bitcoin
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

from price_common import PriceInfo, PriceInfoSingle
from price_binance import BinancePriceSource
from price_bitstamp import BitstampPriceSource
from price_coinbase import CoinbasePriceSource
from price_kraken import KrakenPriceSource

from datetime import datetime, UTC
import threading;

PREFETCH_MIN_ACCEPTED_AGE_SECS: int = 15
PREFETCH_PREF_MAX_AGE_SECS: int = 2

# Can provide current price infos
class PriceSource:
    def __init__(self):
        self.sources = []
        print("PriceSource init")

    def init_sources(self):
        bitstamp_source = BitstampPriceSource()
        # binance_global_source = BinancePriceSource(True)
        binance_us_source = BinancePriceSource(False)
        kraken_source = KrakenPriceSource()
        coinbase_source = CoinbasePriceSource()

        self.sources = [
            bitstamp_source,
            binance_us_source,
            kraken_source,
            coinbase_source,
        ]

        print(f"PriceSource init, with sources: ", end='')
        for s in self.sources:
            print(s.get_source_id(), " ", end='')
        print()

    def get_symbols(self) -> list[str]:
        return ["BTCUSD", "BTCEUR"]

    # Return current price (info).
    def get_price_info(self, symbol: str, pref_max_age: float = 0) -> PriceInfo:
        # lazy init:
        if len(self.sources) == 0:
            self.init_sources()

        price_info = self.get_price_info_internal(symbol, pref_max_age)

        # Optional pre-fetch: if current info is old (but acceptable), start fetch in background
        now = datetime.now(UTC).timestamp()
        age = now - price_info.retrieve_time
        # print(f"Age: {age}")
        if age > max(PREFETCH_MIN_ACCEPTED_AGE_SECS, pref_max_age / 2):
            th1 = threading.Thread(target=self._bg_prefetch, args=(symbol,))
            th1.start() # fire and forget

        return price_info

    def get_price_info_internal(self, symbol: str, pref_max_age: float = 0) -> PriceInfo:
        symbol = symbol.upper()

        # Invoke all sources. Invoke then in parallel, unless fast result is available
        n = len(self.sources)
        thids = []
        price_infos = [None] * n
        for i in range(n):
            price_infos[i] = self.sources[i].get_price_info_fast(symbol, pref_max_age)
            if price_infos[i] is not None:
                continue
            # Fast info not available, invoke in bg thread
            # print(f"Getting price from {self.sources[i].get_source_id()} in bg ...")
            th = threading.Thread(target=self._bg_get_price, args=(self.sources[i], symbol, pref_max_age, price_infos, i))
            th.start()
            thids.append(th)
        # Wait for bg threads
        if len(thids) > 0:
            # print(f"Waiting for bg prices, completion of {len(thids)} threads...")
            for th in thids:
                th.join()

        # Aggregate info from multiple sources
        price_info = PriceSource.aggregate_infos(price_infos, symbol)
        return price_info

    def _bg_get_price(self, price_source, symbol, pref_max_age, result_arr, index):
        try:
            price_info = price_source.get_price_info(symbol, pref_max_age)
        except Exception as ex:
            now = datetime.now(UTC).timestamp()
            price_info = PriceInfoSingle.create_with_error(symbol, now, self.source_id, f"Exception while getting price {ex}")
        result_arr[index] = price_info
        # print(index, len(result_arr), result_arr[index])
        return

    def _bg_prefetch(self, symbol):
        # print(f"Prefetch in background ...")
        _pi = self.get_price_info_internal(symbol, pref_max_age=PREFETCH_PREF_MAX_AGE_SECS)
        # now = datetime.now(UTC).timestamp()
        # age = now - _pi.retrieve_time
        # print(f"Prefetch in background: age {age}  {_pi.price}")
        return

    def aggregate_infos(price_infos: list[PriceInfoSingle], symbol):
        # separate valid and invalid ones
        valc = 0
        invc = 0
        vals = ""
        invs = ""
        valpis = []
        for i in range(len(price_infos)):
            pi = price_infos[i]
            if pi.price == 0 or pi.error:
                invc += 1
                if len(invs) > 0:
                    invs += ","
                invs += str(pi.source)
            else:
                valpis.append(pi)
                valc += 1
                if len(vals) > 0:
                    vals += ","
                vals += str(pi.source)
        src = PriceSource.aggregate_source(valc, vals, invs)
        if valc == 0:
            # no valid price
            now = datetime.now(UTC).timestamp()
            return PriceInfo.create_with_error(symbol, now, src, price_infos, "No source with valid data, can't aggregate")
        p = 0
        min_retrieve_time = valpis[0].retrieve_time
        min_claimed_time = valpis[0].claimed_time
        if valc == 1:
            # one valid price
            p = valpis[0].price
        else:
            # multiple valid prices, take average. Time is oldest
            sp = 0
            t = valpis[0].retrieve_time
            for i in range(len(valpis)):
                sp += valpis[i].price
                if valpis[i].retrieve_time < min_retrieve_time:
                    min_retrieve_time = valpis[i].retrieve_time
                if valpis[i].claimed_time < min_claimed_time:
                    min_claimed_time = valpis[i].claimed_time
            p = sp / float(valc)

        # Compute and set delta_from_aggr's
        for pi in price_infos:
            delta = pi.price - p
            pi.delta_from_aggr = delta

        return PriceInfo(p, symbol, min_retrieve_time, min_claimed_time, src, price_infos, None)

    def aggregate_source(valid_count, valid_sources, invalid_sources):
        s = "Multi{cnt:" + str(valid_count) + ","
        if len(valid_sources) > 0:
            s += "good:[" + valid_sources + "]"
        if len(valid_sources) > 0 and len(invalid_sources) > 0:
            s += ";"
        if len(invalid_sources) > 0:
            s += "bad:[" + invalid_sources + "]"
        s += "}"
        return s


