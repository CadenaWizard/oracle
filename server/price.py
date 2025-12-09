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
        if valc == 1:
            # one valid price
            p = valpis[0].price
            t = valpis[0].retrieve_time
        else:
            # multiple valid prices, take average
            sp = 0
            st = 0
            for i in range(len(valpis)):
                sp += valpis[i].price
                st += valpis[i].retrieve_time
            p = sp / float(valc)
            t = st / float(valc)
        return PriceInfo(p, symbol, t, src, price_infos, None)

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

# # Provide a dummy, algorithmically computed price
# class DummyPriceSource:
#     def get_price_info(symbol, t: int) -> PriceInfo:
#         if t == 0:
#             t = datetime.now(UTC).timestamp()
#         price = DummyPriceSource.get_price(t, symbol)
#         return PriceInfo(price, symbol, t, "Dummy!")

#     def get_price(t: int, symbol) -> int:
#         # Come up with a deterministic non-constant plausible value
#         base_btcusd = 60000 + (t - 1704067200) / 1000 + (t / 2345) % 1000
#         if symbol.upper() == "BTCUSD":
#             return round(base_btcusd)
#         if symbol.upper() == "BTCEUR":
#             return round(base_btcusd * 0.9)
#         # everything else
#         return round(base_btcusd / 10)

