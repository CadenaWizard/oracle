from dto import DigitOutcome, Nonce, OutcomeDto
from oracle import Event, EventClass, EventDescription, Nonces, Outcome
from test_common import initialize_cryptlib_direct

import unittest


class EventDescriptionTestClass(unittest.TestCase):
    def test_properties(self):
        e = EventDescription("BTCUSD", 8, 0, "signer_key1")

        self.assertEqual(e.get_minimum_value(), 0)
        self.assertEqual(e.get_unit(), 1)
        self.assertEqual(e.get_digit_high_pos(), 7)
        self.assertEqual(e.get_maximum_value(), 99_999_999)
        self.assertEqual(e.event_string_template, "Outcome:{event_id}:{digit_index}:{digit_outcome}")

    def test_digit_pos(self):
        e = EventDescription("BTCUSD", 6, 2, "signer_key1")
        self.assertEqual(e.get_minimum_value(), 0)
        self.assertEqual(e.get_unit(), 100)
        self.assertEqual(e.get_digit_high_pos(), 7)
        self.assertEqual(e.get_maximum_value(), 99_999_900)

        e = EventDescription("BTCUSD", 5, 3, "signer_key1")
        self.assertEqual(e.get_minimum_value(), 0)
        self.assertEqual(e.get_unit(), 1000)
        self.assertEqual(e.get_digit_high_pos(), 7)
        self.assertEqual(e.get_maximum_value(), 99_999_000)

        e = EventDescription("BTCUSD", 4, 4, "signer_key1")
        self.assertEqual(e.get_minimum_value(), 0)
        self.assertEqual(e.get_unit(), 10000)
        self.assertEqual(e.get_digit_high_pos(), 7)
        self.assertEqual(e.get_maximum_value(), 99_990_000)

        e = EventDescription("BTCUSD", 6, 4, "signer_key1")
        self.assertEqual(e.get_minimum_value(), 0)
        self.assertEqual(e.get_unit(), 10000)
        self.assertEqual(e.get_digit_high_pos(), 9)
        self.assertEqual(e.get_maximum_value(), 9_999_990_000)

    def test_value_to_digits(self):
        e = EventDescription("BTCUSD", 6, 2, "signer_key1")
        self.assertEqual(e.value_to_digits(1), [0, 0, 0, 0, 0, 0])
        self.assertEqual(e.value_to_digits(200), [0, 0, 0, 0, 0, 2])
        self.assertEqual(e.value_to_digits(200), [0, 0, 0, 0, 0, 2])
        self.assertEqual(e.value_to_digits(99_999_999), [9, 9, 9, 9, 9, 9])
        self.assertEqual(e.value_to_digits(123_456), [0, 0, 1, 2, 3, 5])

        self.assertEqual(e.digits_to_value([0, 0, 0, 0, 0, 1]), 100)
        self.assertEqual(e.digits_to_value([1, 2, 3, 4, 5, 6]), 12_345_600)
        self.assertEqual(e.digits_to_value([0, 0, 1, 2, 3, 5]), 123_500)

        e = EventDescription("BTCUSD", 5, 3, "signer_key1")
        self.assertEqual(e.value_to_digits(123_456), [0, 0, 1, 2, 3])

        self.assertEqual(e.digits_to_value([0, 0, 0, 0, 1]), 1000)
        self.assertEqual(e.digits_to_value([1, 2, 3, 4, 5]), 12_345_000)
        self.assertEqual(e.digits_to_value([0, 0, 1, 2, 3]), 123_000)

        e = EventDescription("BTCUSD", 4, 4, "signer_key1")
        self.assertEqual(e.value_to_digits(123_456), [0, 0, 1, 2])

        self.assertEqual(e.digits_to_value([0, 0, 0, 1]), 10000)
        self.assertEqual(e.digits_to_value([1, 2, 3, 4]), 12_340_000)
        self.assertEqual(e.digits_to_value([0, 0, 1, 2]), 120_000)

        e = EventDescription("BTCUSD", 6, 4, "signer_key1")
        self.assertEqual(e.value_to_digits(123_456), [0, 0, 0, 0, 1, 2])

        self.assertEqual(e.digits_to_value([0, 0, 0, 0, 0, 1]), 10000)
        self.assertEqual(e.digits_to_value([1, 2, 3, 4, 5, 6]), 1_234_560_000)
        self.assertEqual(e.digits_to_value([0, 0, 0, 0, 1, 2]), 120_000)

    def test_template(self):
        e = EventDescription("BTCUSD", 8, 0, "signer_key1")
        event_id = "EID003"
        template = e.event_string_template_for_id(event_id)
        assert event_id in template, "EventID should be included in the template"
        self.assertEqual(template, "Outcome:EID003:{digit_index}:{digit_outcome}")

    def test_to_info(self):
        e = EventDescription("BTCUSD", 8, 0, "signer_key1")
        info = e.to_info()
        expected = {
            'definition': 'BTCUSD',
            'event_type': 'numeric',
            'range_digit_high_pos': 7,
            'range_digit_low_pos': 0,
            'range_digits': 8,
            'range_max_value': 99999999,
            'range_min_value': 0,
            'range_unit': 1,
            "signer_public_key": "signer_key1",
        }
        self.assertEqual(info, expected)


class EventClassTestCase(unittest.TestCase):
    def event_obj(self):
        return EventClass.new("btcusd", 1762988557, "BTCUSD", 8, 0, 1704067200, 86400, 2019682800, "signer_key")

    def test_to_info(self):
        e = self.event_obj()
        info = e.to_info()
        expected = {
            "class_id": "btcusd",
            "desc": {
                'definition': 'BTCUSD',
                'event_type': 'numeric',
                'range_digit_high_pos': 7,
                'range_digit_low_pos': 0,
                'range_digits': 8,
                'range_max_value': 99999999,
                'range_min_value': 0,
                'range_unit': 1,
                "signer_public_key": "signer_key",
            },
            "repeat_first_time": 1704067200,
            "repeat_period": 86400,
            "repeat_offset": 0,
            "repeat_last_time": 2019682800
        }
        self.assertEqual(info, expected)

    def test_next_event_time(self):
        e = self.event_obj()
        self.assertEqual(e.next_event_time(1704067200), 1704067200)
        self.assertEqual(e.next_event_time(1704067201), 1704153600)
        self.assertEqual(e.next_event_time(1704153599), 1704153600)
        self.assertEqual(e.next_event_time(1704153600), 1704153600)
        self.assertEqual(e.next_event_time(1704153601), 1704240000)
        self.assertEqual(e.next_event_time(1704160000), 1704240000)
        self.assertEqual(e.next_event_time(1704240000), 1704240000)
        self.assertEqual(e.next_event_time(1704240001), 1704326400)
        self.assertEqual(e.next_event_time(1714736400), 1714780800)
        self.assertEqual(e.next_event_time(2019600000), 2019600000)
        # Too early
        self.assertEqual(e.next_event_time(1704060000), 1704067200)
        # Out of range
        self.assertEqual(e.next_event_time(2019600001), 0)
        self.assertEqual(e.next_event_time(2019682800), 0)
        # Out of range
        self.assertEqual(e.next_event_time(2020000000), 0)

    def test_next_event_id(self):
        e = self.event_obj()
        self.assertEqual(e.next_event_id(1704067200), "btcusd1704067200")
        self.assertEqual(e.next_event_id(1704067201), "btcusd1704153600")
        self.assertEqual(e.next_event_id(1704153599), "btcusd1704153600")
        self.assertEqual(e.next_event_id(1704153600), "btcusd1704153600")
        self.assertEqual(e.next_event_id(1704153601), "btcusd1704240000")
        self.assertEqual(e.next_event_id(1704160000), "btcusd1704240000")
        self.assertEqual(e.next_event_id(1704240000), "btcusd1704240000")
        self.assertEqual(e.next_event_id(1704240001), "btcusd1704326400")
        self.assertEqual(e.next_event_id(1714736400), "btcusd1714780800")
        self.assertEqual(e.next_event_id(2019600000), "btcusd2019600000")
        # Out of range
        self.assertEqual(e.next_event_id(2019600001), None)
        self.assertEqual(e.next_event_id(2019682800), None)
        # Out of range
        self.assertEqual(e.next_event_id(2020000000), None)

    def test_next_event_many(self):
        e = self.event_obj()
        # Early
        for i in range(10):
            t = 1704067200 + (i - 10) * 307.5
            self.assertEqual(e.next_event_time(t), 1704067200)
        # In between
        for i in range(100):
            t = 1704067200 + i * 16356.25
            n = e.next_event_time(t)
            self.assertTrue(n >= t)
            self.assertTrue(n >= 1704067200)
            self.assertTrue(n <= 2019682800)
            self.assertTrue(n % 86400 == 0)
        # Later
        for i in range(10):
            t = 2019600000 + 1 + i * 37.5
            self.assertEqual(e.next_event_time(t), 0)

    def test_next_event_with_offset(self):
        offset = 13
        start = 1704067200 + offset
        end = 2019682800 + offset
        e = EventClass.new("btcusd", 1762988557, "BTCUSD", 8, 0, start, 86400, end, "signer_key")
        # Early
        for i in range(10):
            t = start + (i - 10) * 307.5
            self.assertEqual(e.next_event_time(t), start)
        # In between
        for i in range(100):
            t = start + i * 16356.25
            n = e.next_event_time(t)
            self.assertTrue(n >= t)
            self.assertTrue(n >= start)
            self.assertTrue(n <= end)
            self.assertTrue(n % 86400 == offset)
        # Later
        for i in range(10):
            t = end + 1 + i * 37.5
            self.assertEqual(e.next_event_time(t), 0)

class DigitOutcomeTestCase(unittest.TestCase):
    def test_to_info(self):
        event_id = "event001"
        d = DigitOutcome(event_id, 1, 7, "nonce01", "sig01", "msg_to_Sign_01")
        self.assertEqual(d.to_info(), {'index': 1, 'msg_str': 'msg_to_Sign_01', 'nonce': 'nonce01', 'signature': 'sig01', 'value': 7})
        d = DigitOutcome(event_id, 4, 9, "nonce02", "sig02", "msg_to_Sign_02")
        self.assertEqual(d.to_info(), {'index': 4, 'msg_str': 'msg_to_Sign_02', 'nonce': 'nonce02', 'signature': 'sig02', 'value': 9})


class NonceTestCase(unittest.TestCase):
    def test_init(self):
        n1 = Nonce("event001", 0, "npub001", "nsec0001")
        self.assertEqual(n1.nonce_sec, "nsec0001")
        n2 = Nonce("event001", 0, "npub002", "nsec0002")
        self.assertEqual(n2.nonce_sec, "nsec0002")


class NoncesTestCase(unittest.TestCase):
    def test_generate(self):
        nonces = Nonces.generate("event001", 9)
        self.assertEqual(len(nonces), 9)
        self.assertEqual(nonces[3].event_id, "event001")
        self.assertEqual(nonces[3].digit_index, 3)
        self.assertEqual(len(nonces[3].nonce_sec), 64)


class OutcomeTestCase(unittest.TestCase):
    def setUp(self):
        initialize_cryptlib_direct()

    def test_init(self):
        event_id = "event123"
        odto = OutcomeDto(event_id, "88000", 2019600000)
        digits = []
        for i in range(0, 7):
            d = DigitOutcome(event_id, i, int(i/2)+1, "npub0"+str(i), "sig0"+str(i), "msg_to_Sign_0"+str(i))
            digits.append(d)
        o = Outcome(dto=odto, digit_outcomes=digits)
        self.assertEqual(o.dto.event_id, event_id)
        self.assertEqual(len(o.digits), 7)
        self.assertEqual(o.digits[4].to_info(), {'index': 4, 'msg_str': 'msg_to_Sign_04', 'nonce': 'npub04', 'signature': 'sig04', 'value': 3})

    def test_create(self):
        event_id = "event123"
        digits = 7
        desc = EventDescription("BTCUSD", digits, 0, "signer_key1")
        nonces = Nonces.generate(event_id, digits)
        outcome_value = "88001.52"
        o = Outcome.create(outcome_value=outcome_value, event_id=event_id, event_desc=desc, created_time=2019600000, nonces=nonces)
        self.assertEqual(o.dto.event_id, event_id)
        self.assertEqual(len(o.digits), digits)
        a_digit_info = o.digits[3].to_info()
        # Nonce and sig is variable, replace them
        a_digit_info['nonce'] = '<var_nonce>'
        a_digit_info['signature'] = '<var_signature>'
        self.assertEqual(a_digit_info, {
            'index': 3,
            'msg_str': 'Outcome:event123:3:8',
            'nonce': '<var_nonce>',
            'signature': '<var_signature>',
            'value': 8,
        })
        digits = list(map(lambda d: d.value, o.digits))
        self.assertEqual(digits, [0, 0, 8, 8, 0, 0, 2])

        # Too few nonces
        nonces4 = Nonces.generate(event_id, 4)
        self.assertRaises(Exception, Outcome.create, outcome_value=outcome_value, event_id=event_id, event_desc=desc, created_time=2019600000, nonces=nonces4)
        # Invalid non-umeric value string
        self.assertRaises(Exception, Outcome.create, outcome_value="non_numeric_88000", event_id=event_id, event_desc=desc, created_time=2019600000, nonces=nonces)


class EventTestCase(unittest.TestCase):
    def test_new(self):
        class_id = "btcusd1"
        definition = "BTCUSD"
        event_class = EventClass.new(class_id, 1762988557, definition, 8, 0, 1704067200, 86400, 2019682800, "signer_key")
        time = 1704067200 + 13 * 86400
        id = definition.lower() + str(time)
        e = Event.new(
            time=time,
            event_class=event_class,
        )
        self.assertEqual(e.dto.event_id, id)
        self.assertEqual(e.event_class_id, class_id)
        self.assertEqual(e.dto.time, time)
        self.assertEqual(e.dto.signer_public_key, "signer_key")
        self.assertEqual(e.dto.string_template, "Outcome:btcusd1705190400:{digit_index}:{digit_outcome}")


if __name__ == "__main__":
    unittest.main() # run all tests

