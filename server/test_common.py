from db import db_setup_from_to
from price_common import PriceInfoSingle
import dlccryptlib_oracle

from datetime import datetime, UTC
import sqlite3
import os


DUMMY_ENTROPY = "01010101010101010101010101010101"
DUMMY_ENTROPY_2 = "01010101010101010101010101010102"

# Initialize cryptlib directly (without using a secret file) with a dummy entropy
# Return Xpub and default (0th) pubkey
def initialize_cryptlib_direct_dummy():
    return initialize_cryptlib_direct(DUMMY_ENTROPY, "signet")


# Initialize cryptlib directly (without using a secret file)
# Return Xpub and default (0th) pubkey
def initialize_cryptlib_direct(entropy_hex: str, network: str):
    xpub = dlccryptlib_oracle.init_with_entropy(entropy_hex, network)
    pubkey = dlccryptlib_oracle.get_public_key(0)
    print(f"cryptlib initialized, xpub: {xpub}  pubkey: {pubkey}")
    return xpub, pubkey


def prepare_test_secret_for_cryptlib():
    # Prepare variables for secret key file for testing, to point to test file
    secret_file = "./testdata/dummy_test_secret.sec"
    assert(os.path.exists(secret_file))
    os.environ["KEY_SECRET_FILE_NAME"] = secret_file
    os.environ["KEY_SECRET_PWD"] = "password"
    os.environ["EXTRA_KEY_SECRETS"] = ""


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


# A KeyManager that is useful for testing (doesn't need encrypted secret files)
class TestKeyManager:
    def __init__(self, add_extra_key: bool = False):
        self.network = "signet"
        self.public_keys = []
        self.dummy_entropies = []
        self.public_keys.append("__placeholder__")
        self.dummy_entropies.append("__placeholder__")

        if add_extra_key:
            # Optional extra key
            entropy = DUMMY_ENTROPY_2
            _xpub, pubkey = initialize_cryptlib_direct(entropy, self.network)
            self.public_keys.append(pubkey)
            self.dummy_entropies.append(entropy)

        # Main key
        entropy = DUMMY_ENTROPY
        _xpub, pubkey = initialize_cryptlib_direct(entropy, self.network)
        self.public_keys[0] = pubkey
        self.dummy_entropies[0] = entropy
        print(f"TestKeyManager initialized:")
        for i in range(len(self.public_keys)):
            print(f"    {self.public_keys[i]} {self.dummy_entropies[i]}")

    def keys_init(self) -> list[str]:
        return self.public_keys

    def keys_init_with_public_key(self, public_key: str) -> bool:
        # Find the matching entropy
        for i in range(len(self.public_keys)):
            if public_key == self.public_keys[i]:
                entropy = self.dummy_entropies[i]
                _xpub, pubkey = initialize_cryptlib_direct(entropy, self.network)
                assert(pubkey == public_key)
                return
        # Key not found
        raise Exception(f"Public key not found {public_key}")


# A test mock for PriceSource, returns a constant price
class PriceSourceMockConstant:
    def __init__(self, const_price: float):
        self.const_price = const_price
        self.symbol_rates = {
            'BTCUSD': 1.0,
            'BTCEUR': 0.9,
        }

    def get_price_info(self, symbol: str, pref_max_age: float = 0) -> PriceInfoSingle:
        now = datetime.now(UTC).timestamp()
        symbol = symbol.upper()
        assert(symbol in self.symbol_rates)
        relative_rate = self.symbol_rates[symbol]
        rate = self.const_price * relative_rate
        return PriceInfoSingle(rate, symbol, now - pref_max_age/2, now - pref_max_age/2, "MockConstant")

