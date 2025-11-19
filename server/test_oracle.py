from db import db_setup_from_to
from oracle import EventClass, EventDescription, Oracle
from test_common import PriceSourceMockConstant, initialize_cryptlib_direct, recreate_empty_db_file

import math
import unittest


class OracleTestClass(unittest.TestCase):
    public_key = "?"
    event_classes = []
    now = 0

    @classmethod
    def setUpClass(cls):
        print("setUpClass")

        _xpub, cls.public_key = initialize_cryptlib_direct()
        repeat_time = 3600
        cls.now = 1762988557
        cls.test_public_key = "0323423d31a856d8d8c8f7fe46ca984ee2cdddcd8506b805417e9c382f637149fd"
        repeat_first_time = int(math.floor(cls.now / repeat_time)) * repeat_time - 7 * repeat_time
        repeat_last_time = repeat_first_time + 37 * repeat_time
        cls.event_classes = [
            EventClass.new("btcusd01", cls.now, "BTCUSD", 7, 0, repeat_first_time, repeat_time, repeat_last_time, cls.test_public_key),
            EventClass.new("btceur01", cls.now, "BTCEUR", 7, 0, repeat_first_time, repeat_time, repeat_last_time, cls.test_public_key),
        ]

    # Helper to create oracle instance
    def create_oracle(self):
        # recreate_empty_db_file()

        # Custom price source
        price_mock = PriceSourceMockConstant(98765)
        o = Oracle(self.public_key, data_dir=".", price_source_override=price_mock)
        return o

    # Create Oracle
    def test_init(self):
        o = self.create_oracle()
        o.print_stats()
        self.assertEqual(o.public_key, self.public_key)
        self.assertEqual(o.db.event_classes_len(), 0)
        self.assertEqual(o.db.events_len(), 0)
        self.assertEqual(o.get_oracle_info()['main_public_key'], '0323423d31a856d8d8c8f7fe46ca984ee2cdddcd8506b805417e9c382f637149fd')
        o.close()

    # Create Oracle and fill with event classes
    def test_load(self):
        o = self.create_oracle()
        o.load_event_classes(self.event_classes)
        o.print_stats()
        self.assertEqual(o.db.event_classes_len(), 2)
        self.assertEqual(o.db.events_len(), 2 * 38)
        # Status, current time is variable
        status = o._get_oracle_status_time(self.now)
        self.assertEqual(status, {
            'current_time_utc': 1762988557,
            'future_event_count': 60,
            'total_event_count': 76,
        })
        o.close()

        get_classes = o.get_event_classes()
        self.assertEqual(len(get_classes), 2)
        self.assertEqual(get_classes[0], {
            'class_id': 'btcusd01',
            'desc': {
                'definition': 'BTCUSD',
                'event_type': 'numeric',
                'range_digit_high_pos': 6,
                'range_digit_low_pos': 0,
                'range_digits': 7,
                'range_max_value': 9999999,
                'range_min_value': 0,
                'range_unit': 1,
                'signer_public_key': '0323423d31a856d8d8c8f7fe46ca984ee2cdddcd8506b805417e9c382f637149fd',
            },
            'repeat_first_time': 1762963200,
            'repeat_period': 3600,
            "repeat_offset": 0,
            'repeat_last_time': 1763096400,
        })

        self.assertEqual(o.get_event_class_latest_by_def('MISSING_DEFINITION'), None)
        self.assertEqual(o.get_event_class_latest_by_def('btcusd').dto.definition, 'BTCUSD')
        self.assertEqual(o.get_event_class_latest_by_def('btcusd').dto.id, 'btcusd01')
        self.assertEqual(o.get_event_class_latest_by_def('btcUSD').dto.definition, 'BTCUSD')

        # Nonexistent ID
        self.assertEqual(o.get_event_by_id('btceur1762970407'), {})

        ev1 = o.get_event_by_id('btceur1762970400')
        self.assertEqual(ev1['time_utc'], 1762970400)
        self.assertEqual(ev1['definition'], 'BTCEUR')

        # Nonces may change
        self.assertEqual(len(ev1['nonces']), 7)
        self.assertEqual(len(ev1['nonces'][0]), 66)
        del ev1['nonces']
        self.assertEqual(ev1, {
            'event_id': 'btceur1762970400',
            'time_utc': 1762970400,
            'time_utc_nice': '2025-11-12 18:00:00+00:00',
            'definition': 'BTCEUR',
            'event_type': 'numeric',
            'range_digits': 7,
            'range_digit_low_pos': 0,
            'range_digit_high_pos': 6,
            'range_unit': 1,
            'range_min_value': 0,
            'range_max_value': 9999999,
            'event_class': 'btceur01',
            'signer_public_key': '0323423d31a856d8d8c8f7fe46ca984ee2cdddcd8506b805417e9c382f637149fd', 'string_template': 'Outcome:btceur1762970400:{digit_index}:{digit_outcome}',
            'has_outcome': False,
        })
        o.close()

    def test_filter(self):
        o = self.create_oracle()
        o.load_event_classes(self.event_classes)
        o.print_stats()

        filtered = o.get_event_ids_filter(self.now - 20000, self.now + 20000, 'btcusd')
        self.assertEqual(len(filtered), 11)
        self.assertEqual(filtered[0], 'btcusd1762970400')
        self.assertEqual(filtered[1], 'btcusd1762974000')
        self.assertEqual(filtered[len(filtered)-1], 'btcusd1763006400')

        # No definition given
        filtered = o.get_event_ids_filter(self.now - 20000, self.now + 20000, None)
        self.assertEqual(len(filtered), 22)
        self.assertEqual(filtered[0], 'btcusd1762970400')
        # self.assertEqual(filtered[10], 'btcusd1763006400')
        # self.assertEqual(filtered[11], 'btceur1762970400')
        self.assertEqual(filtered[10], 'btcusd1762988400')
        self.assertEqual(filtered[11], 'btceur1762988400')
        self.assertEqual(filtered[len(filtered)-1], 'btceur1763006400')

        # No end time given
        filtered = o.get_event_ids_filter(self.now - 20000, 0, 'btcusd')
        self.assertEqual(len(filtered), 36)
        self.assertEqual(filtered[0], 'btcusd1762970400')
        self.assertEqual(filtered[1], 'btcusd1762974000')
        self.assertEqual(filtered[len(filtered)-1], 'btcusd1763096400')

        filtered = o.get_events_filter(self.now - 20000, self.now + 20000, 'btcusd')
        self.assertEqual(len(filtered), 11)
        self.assertEqual(filtered[0]['event_id'], 'btcusd1762970400')
        self.assertEqual(filtered[0]['time_utc'], 1762970400)
        self.assertEqual(filtered[0]['definition'], 'BTCUSD')
        self.assertEqual(filtered[0]['range_digits'], 7)
        self.assertEqual(filtered[0]['has_outcome'], False)
        self.assertEqual(len(filtered[0]['nonces']), 7)
        self.assertEqual(len(filtered[0]['nonces'][0]), 66)
        self.assertEqual(filtered[len(filtered)-1]['event_id'], 'btcusd1763006400')

        o.close()

    def test_next_event(self):
        o = self.create_oracle()
        o.load_event_classes(self.event_classes)
        o.print_stats()

        definition = "BTCUSD"
        time = self.now + 7 * 3600 + 60
        next_event = o._get_next_event_with_time(definition, time)
        self.assertEqual(next_event['event_id'], 'btcusd1763017200')
        self.assertEqual(next_event['time_utc'], 1763017200)
        self.assertEqual(next_event['definition'], definition)
        self.assertEqual(next_event['event_class'], 'btcusd01')
        self.assertEqual(next_event['has_outcome'], False)

        # next-next
        next_next_event = o._get_next_event_with_time(definition, next_event['time_utc'] + 1)
        self.assertEqual(next_next_event['time_utc'], 1763020800)

        o.close()

    # Next event with multiple event classes per definition
    def test_with_multiple_event_classes(self):
        o = self.create_oracle()
        definition = "BTCUSD"
        repeat_time = 3600
        time1 = int(math.floor(self.now / repeat_time)) * repeat_time - 7 * repeat_time
        time2 = time1 + 20 * repeat_time
        time3 = time2 + 20 * repeat_time
        time4 = time3 + 20 * repeat_time
        o.delete_all_contents()
        o.load_event_classes([
            EventClass.new("class01", time1, definition, 7, 0, time1, repeat_time, time2 - 1, self.test_public_key),
            EventClass.new("class02", time2, definition, 7, 0, time2, repeat_time, time3 - 1, self.test_public_key),
            EventClass.new("class03", time3, definition, 7, 0, time3, repeat_time, time4 - 1, self.test_public_key),
        ])
        o.print_stats()

        self.assertEqual(o.get_event_class_latest_by_def('btcusd').dto.id, 'class03')
        self.assertEqual(o.get_event_class_latest_by_def('btcusd').dto.definition, 'BTCUSD')

        # choose one that falls into the middle one
        time = self.now + 17 * 3600 + 60
        next_event = o._get_next_event_with_time(definition, time)
        self.assertEqual(next_event['event_id'], 'btcusd1763053200')
        self.assertEqual(next_event['time_utc'], 1763053200)
        self.assertEqual(next_event['definition'], definition)
        self.assertEqual(next_event['event_class'], 'class02')
        self.assertEqual(next_event['has_outcome'], False)

        o.close()

    def assert_event_has_outcome(self, event, expected_price):
        digits = event['range_digits']
        self.assertEqual(digits, 7)
        event_desc = EventDescription(event['definition'], digits, event['range_digit_low_pos'], event['signer_public_key'])
        expected_price_digits = event_desc.value_to_digits(expected_price)
        self.assertEqual(event['has_outcome'], True)
        self.assertAlmostEqual(float(event['outcome_value']), float(expected_price))
        self.assertEqual(len(event['digits']), 7)
        for i in range(0, digits):
            digit_i = event['digits'][i]
            self.assertEqual(digit_i['index'], i)
            self.assertEqual(digit_i['value'], expected_price_digits[i])
            self.assertEqual(len(digit_i['signature']), 128)

    def test_outcome(self):
        o = self.create_oracle()
        o.load_event_classes(self.event_classes)
        o.print_stats()

        event_id = 'btceur1762970400'
        e1 = o.get_event_by_id(event_id)
        self.assertTrue(e1 != None)
        self.assertEqual(e1['has_outcome'], False)

        # Generate outcomes
        cnt = o._create_past_outcomes_time(self.now)
        self.assertEqual(cnt, 16)

        # get the event, should have outcome
        e2 = o.get_event_by_id(event_id)
        self.assert_event_has_outcome(e2, 88888.5)

        o.close()


if __name__ == "__main__":
    unittest.main() # run all tests



