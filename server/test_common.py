from price_common import PriceInfo
import dlcplazacryptlib


def initialize_cryptlib():
    """Call before every test case."""
    dummy_entropy = "01010101010101010101010101010101"
    xpub = dlcplazacryptlib.init_with_entropy(dummy_entropy, "signet")
    print(f"cryptlib initialized, xpub: {xpub}")
    return xpub


# A test mock for PriceSource, returns a constant price
class PriceSourceMockConstant:
    def __init__(self, const_price: float):
        self.const_price = const_price
        self.symbol_rates = {
            'BTCUSD': 1.0,
            'BTCEUR': 0.9,
        }

    def get_price_info(self, symbol: str, preferred_time: int) -> PriceInfo:
        symbol = symbol.upper()
        assert(symbol in self.symbol_rates)
        relative_rate = self.symbol_rates[symbol]
        rate = self.const_price * relative_rate
        return PriceInfo(rate, symbol, preferred_time, "MockConstant")

