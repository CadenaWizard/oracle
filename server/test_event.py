from oracle import EventDescription

import unittest


class EventDescriptionTestCase(unittest.TestCase):
    def test_properties(self):
        e = EventDescription("BTCUSD", 8, 0)

        self.assertEqual(e.get_minimum_value(), 0)
        self.assertEqual(e.get_unit(), 1)
        self.assertEqual(e.get_digit_high_pos(), 7)
        self.assertEqual(e.get_maximum_value(), 99_999_999)
        self.assertEqual(e.event_string_template(), "Outcome:{event_id}:{digit_index}:{digit_outcome}")

    def test_digit_pos(self):
        e = EventDescription("BTCUSD", 6, 2)
        self.assertEqual(e.get_minimum_value(), 0)
        self.assertEqual(e.get_unit(), 100)
        self.assertEqual(e.get_digit_high_pos(), 7)
        self.assertEqual(e.get_maximum_value(), 99_999_900)

        e = EventDescription("BTCUSD", 5, 3)
        self.assertEqual(e.get_minimum_value(), 0)
        self.assertEqual(e.get_unit(), 1000)
        self.assertEqual(e.get_digit_high_pos(), 7)
        self.assertEqual(e.get_maximum_value(), 99_999_000)

        e = EventDescription("BTCUSD", 4, 4)
        self.assertEqual(e.get_minimum_value(), 0)
        self.assertEqual(e.get_unit(), 10000)
        self.assertEqual(e.get_digit_high_pos(), 7)
        self.assertEqual(e.get_maximum_value(), 99_990_000)

        e = EventDescription("BTCUSD", 6, 4)
        self.assertEqual(e.get_minimum_value(), 0)
        self.assertEqual(e.get_unit(), 10000)
        self.assertEqual(e.get_digit_high_pos(), 9)
        self.assertEqual(e.get_maximum_value(), 9_999_990_000)

    def test_value_to_digits(self):
        e = EventDescription("BTCUSD", 6, 2)
        self.assertEqual(e.value_to_digits(1), [0, 0, 0, 0, 0, 0])
        self.assertEqual(e.value_to_digits(200), [0, 0, 0, 0, 0, 2])
        self.assertEqual(e.value_to_digits(200), [0, 0, 0, 0, 0, 2])
        self.assertEqual(e.value_to_digits(99_999_999), [9, 9, 9, 9, 9, 9])
        self.assertEqual(e.value_to_digits(123_456), [0, 0, 1, 2, 3, 5])

        self.assertEqual(e.digits_to_value([0, 0, 0, 0, 0, 1]), 100)
        self.assertEqual(e.digits_to_value([1, 2, 3, 4, 5, 6]), 12_345_600)
        self.assertEqual(e.digits_to_value([0, 0, 1, 2, 3, 5]), 123_500)

        e = EventDescription("BTCUSD", 5, 3)
        self.assertEqual(e.value_to_digits(123_456), [0, 0, 1, 2, 3])

        self.assertEqual(e.digits_to_value([0, 0, 0, 0, 1]), 1000)
        self.assertEqual(e.digits_to_value([1, 2, 3, 4, 5]), 12_345_000)
        self.assertEqual(e.digits_to_value([0, 0, 1, 2, 3]), 123_000)

        e = EventDescription("BTCUSD", 4, 4)
        self.assertEqual(e.value_to_digits(123_456), [0, 0, 1, 2])

        self.assertEqual(e.digits_to_value([0, 0, 0, 1]), 10000)
        self.assertEqual(e.digits_to_value([1, 2, 3, 4]), 12_340_000)
        self.assertEqual(e.digits_to_value([0, 0, 1, 2]), 120_000)

        e = EventDescription("BTCUSD", 6, 4)
        self.assertEqual(e.value_to_digits(123_456), [0, 0, 0, 0, 1, 2])

        self.assertEqual(e.digits_to_value([0, 0, 0, 0, 0, 1]), 10000)
        self.assertEqual(e.digits_to_value([1, 2, 3, 4, 5, 6]), 1_234_560_000)
        self.assertEqual(e.digits_to_value([0, 0, 0, 0, 1, 2]), 120_000)

    def test_template(self):
        e = EventDescription("BTCUSD", 8, 0)
        event_id = "EID003"
        template = e.event_string_template_for_id(event_id)
        assert event_id in template, "EventID should be included in the template"
        self.assertEqual(template, "Outcome:EID003:{digit_index}:{digit_outcome}")

    def test_to_info(self):
        e = EventDescription("BTCUSD", 8, 0)
        info = e.to_info()
        expected = {
            'definition': 'BTCUSD',
            'event_type': 'numeric',
            'range_digit_high_pos': 7,
            'range_digit_low_pos': 0,
            'range_digits': 8,
            'range_max_value': 99999999,
            'range_min_value': 0,
            'range_unit': 1
        }
        self.assertEqual(info, expected)


if __name__ == "__main__":
    unittest.main() # run all tests
