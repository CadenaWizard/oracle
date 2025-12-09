from db import db_setup_from_to
from price_common import PriceInfoSingle
import dlcplazacryptlib

from datetime import datetime, UTC
import sqlite3
import os


DUMMY_ENTROPY = "01010101010101010101010101010101"

# Return Xpub and default (0th) pubkey
def initialize_cryptlib_direct():
    xpub = dlcplazacryptlib.init_with_entropy(DUMMY_ENTROPY, "signet")
    pubkey = dlcplazacryptlib.get_public_key(0)
    print(f"cryptlib initialized, xpub: {xpub}  pubkey: {pubkey}")
    return xpub, pubkey


def prepare_test_secret_for_cryptlib():
    # Prepare variables for secret key file for testing, to point to test file
    secret_file = "./testdata/dummy_test_secret.sec"
    assert(os.path.exists(secret_file))
    os.environ["KEY_SECRET_FILE_NAME"] = secret_file
    os.environ["KEY_SECRET_PWD"] = "password"


def recreate_empty_db_file(dbfile: str = "./ora.db"):
    if os.path.exists(dbfile):
        os.remove(dbfile)
    conn = sqlite3.connect(dbfile)
    # Explicitely enable Foreign Key support!
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = TRUE")
    cursor.close()
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

    def get_price_info(self, symbol: str, _pref_max_age: float = 0) -> PriceInfoSingle:
        now = datetime.now(UTC).timestamp()
        symbol = symbol.upper()
        assert(symbol in self.symbol_rates)
        relative_rate = self.symbol_rates[symbol]
        rate = self.const_price * relative_rate
        return PriceInfoSingle(rate, symbol, now, now, "MockConstant")

