from util import HexValue, power_of_ten

import unittest


class UtilTestCase(unittest.TestCase):
    def test_power_of_10(self):
        # check all values 0--10
        expected = 1
        for exponent in range(0, 11):
            self.assertEqual(power_of_ten(exponent), expected, f"Expected {expected} for power_of_ten({exponent})")
            expected *= 10

        # negative input raises exception
        self.assertRaises(Exception, power_of_ten, -1)

    def test_hex_value(self):
        self.assertEqual(HexValue.get_default_len(25), "0123456789012345678901234")


if __name__ == "__main__":
    unittest.main() # run all tests
