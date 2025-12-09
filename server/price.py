# Copyright (c) 2025-present Cadena Bitcoin
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

from price_common import PriceInfo, PriceInfoSingle
from price_binance import BinancePriceSource
from price_bitstamp import BitstampPriceSource
from datetime import datetime, UTC

# Can provide current price infos
class PriceSource:
    def __init__(self):
        self.bitstamp_source = BitstampPriceSource()
        # binance_global_source = BinancePriceSource(True)
        self.binance_us_source = BinancePriceSource(False)

    def get_symbols(self) -> list[str]:
        return ["BTCUSD", "BTCEUR"]

    # Return current price (info).
    # Supplied time is only a hint (used in case of dummy)
    def get_price_info(self, symbol: str, preferred_time: int) -> PriceInfo:
        symbol = symbol.upper()
        price_infos = []

        # TODO parallelize
        price_infos.append(self.bitstamp_source.get_price_info(symbol, preferred_time))
        # price_infos.append(self.binance_global_source.get_price_info(symbol, preferred_time))
        price_infos.append(self.binance_us_source.get_price_info(symbol, preferred_time))

        # Aggregate info from multiple sources
        price_info = PriceSource.aggregate_infos(price_infos, symbol, preferred_time)
        return price_info

    def aggregate_infos(price_infos: list[PriceInfoSingle], symbol, preferred_time):
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
            return PriceInfo.create_with_error(symbol, preferred_time, src, price_infos, "No source with valid data, can't aggregate")
        p = 0
        t = 0
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


