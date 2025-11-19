from db import db_setup_from_to
from price_common import PriceInfo
import dlcplazacryptlib

import sqlite3
import os


DUMMY_ENTROPY = "01010101010101010101010101010101"

def initialize_cryptlib_direct():
    xpub = dlcplazacryptlib.init_with_entropy(DUMMY_ENTROPY, "signet")
    print(f"cryptlib initialized, xpub: {xpub}")
    return xpub


def prepare_test_secret_for_cryptlib():
    # Prepare secret key file for testing, from checked-in test file
    secret_file_name = "./secret.sec"
    if not os.path.exists(secret_file_name):
        copycmd = f"cp ./testdata/dummy_test_secret.sec {secret_file_name}"
        print(copycmd)
        os.system(copycmd)
    assert(os.path.exists(secret_file_name))


def recreate_empty_db_file():
    dbfile = "./ora.db"
    if os.path.exists(dbfile):
        os.remove(dbfile)
    conn = sqlite3.connect(dbfile)
    db_setup_from_to(conn)
    conn.close()


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

