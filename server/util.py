# Copyright (c) 2025-present Cadena Bitcoin
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

import random


HEX_ALPHABET = "0123456789abcdef"

class HexValue:
    def get_default():
        return "0102030405060708091011121314151617181920212323242526272829303132"

    def get_random():
        return HexValue.get_random_len(32)

    def get_default_len(l: int):
        s = ""
        cnt = 0
        while len(s) < l:
            s += str(cnt)
            cnt = (cnt +1) % 10
        return s

    def get_random_len(l: int):
        s = ""
        while len(s) < l:
            s += HEX_ALPHABET[random.randrange(16)]
        return s


# Get power of 10 (global helper)
def power_of_ten(exponent: int) -> int:
    if exponent < 0:
        raise Exception(f"Invalid negative power of 10 {exponent}")
    # Quick lookup
    if exponent <= 6:
        return [1, 10, 100, 1000, 10000, 100000, 1000000][exponent]
    # General, multiplication
    pow = 1
    for _i in range(exponent):
        pow *= 10
    return pow

