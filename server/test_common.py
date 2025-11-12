import dlcplazacryptlib


def initialize_cryptlib():
    """Call before every test case."""
    dummy_entropy = "01010101010101010101010101010101"
    xpub = dlcplazacryptlib.init_with_entropy(dummy_entropy, "signet")
    print(f"cryptlib initialized, xpub: {xpub}")
