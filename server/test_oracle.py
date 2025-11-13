from oracle import EventClass, Oracle
from test_common import initialize_cryptlib

import math
import unittest


class OracleTestCase(unittest.TestCase):
    public_key = "?"
    event_classes = []
    now = 0

    def setUp(self):
        self.public_key = initialize_cryptlib()
        repeat_time = 3600
        self.now = 1762988557
        start_time = int(math.floor(self.now / repeat_time)) * repeat_time - 7 * repeat_time
        end_time = start_time + 37 * repeat_time
        self.event_classes = [
            EventClass.new("btcusd", "BTCUSD", 7, 0, start_time, repeat_time, end_time),
            EventClass.new("btceur", "BTCEUR", 7, 0, start_time, repeat_time, end_time),
        ]


    # Create Oracle
    def test_init(self):
        o = Oracle(self.public_key)
        o.print()
        self.assertEqual(o.public_key, self.public_key)
        self.assertEqual(o.db.event_classes_len(), 0)
        self.assertEqual(o.db.events_len(), 0)
        self.assertEqual(o.get_oracle_info(), {'public_key': 'tpubDCSYyor6BehdMVD2mcvVyGLcGyUxJASV2WH7MDxEULG5WD9iXx36nuABqiLDrM5tWBGUTqYb3Sx4kePh2Uk3zu9gPJsYru2AnfHjVYSocJG'})

    # Create Oracle and fill with event classes
    def test_load(self):
        o = Oracle(self.public_key)
        o.load_event_classes(self.event_classes)
        o.print()
        self.assertEqual(o.db.event_classes_len(), 2)
        self.assertEqual(o.db.events_len(), 2 * 38)
        # Status, current time is variable
        status = o._get_oracle_status_time(self.now)
        status['current_time_utc'] = 123
        self.assertEqual(status, {
            'current_time_utc': 123,
            'future_event_count': 60,
            'total_event_count': 76,
        })

        get_classes = o.get_event_classes()
        self.assertEqual(len(get_classes), 2)
        self.assertEqual(get_classes[0], {
            'class_id': 'btcusd',
            'desc': {
                'definition': 'BTCUSD',
                'event_type': 'numeric',
                'range_digit_high_pos': 6,
                'range_digit_low_pos': 0,
                'range_digits': 7,
                'range_max_value': 9999999,
                'range_min_value': 0,
                'range_unit': 1,
            },
            'repeat_first_time': 1762963200,
            'repeat_last_time': 1763096400,
            'repeat_period': 3600,
        })

        self.assertEqual(o.get_event_class('MISSING_DEFINITION'), None)
        self.assertEqual(o.get_event_class('btcusd').dto.definition, 'BTCUSD')
        self.assertEqual(o.get_event_class('btcUSD').dto.definition, 'BTCUSD')

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
            'event_class': 'btceur',
            'signer_public_key': 'tpubDCSYyor6BehdMVD2mcvVyGLcGyUxJASV2WH7MDxEULG5WD9iXx36nuABqiLDrM5tWBGUTqYb3Sx4kePh2Uk3zu9gPJsYru2AnfHjVYSocJG', 'string_template': 'Outcome:btceur1762970400:{digit_index}:{digit_outcome}',
            'has_outcome': False,
        })

    def test_filter(self):
        o = Oracle(self.public_key)
        o.load_event_classes(self.event_classes)
        o.print()

        filtered = o.get_event_ids_filter(self.now - 20000, self.now + 20000, 'btcusd')
        self.assertEqual(len(filtered), 11)
        self.assertEqual(filtered[0], 'btcusd1762970400')
        self.assertEqual(filtered[1], 'btcusd1762974000')
        self.assertEqual(filtered[len(filtered)-1], 'btcusd1763006400')

        # No definition given
        filtered = o.get_event_ids_filter(self.now - 20000, self.now + 20000, None)
        self.assertEqual(len(filtered), 22)
        self.assertEqual(filtered[0], 'btcusd1762970400')
        self.assertEqual(filtered[10], 'btcusd1763006400')
        self.assertEqual(filtered[11], 'btceur1762970400')
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

    def assert_event_has_outcome(self, event):
        self.assertEqual(event['has_outcome'], True)
        # TODO: outcome price varies, should be stubbed
        self.assertEqual(len(event['digits']), 7)
        digit5 = event['digits'][5]
        self.assertEqual(digit5['index'], 5)
        self.assertEqual(len(digit5['signature']), 128)

    def test_outcome(self):
        o = Oracle(self.public_key)
        o.load_event_classes(self.event_classes)
        o.print()

        event_id = 'btceur1762970400'
        e1 = o.get_event_by_id(event_id)
        self.assertTrue(e1 != None)
        self.assertEqual(e1['has_outcome'], False)

        # Generate outcomes
        cnt = o.create_past_outcomes_time(self.now)
        self.assertTrue(cnt >= 10)

        # get the event, should have outcome
        e2 = o.get_event_by_id(event_id)
        self.assert_event_has_outcome(e2)

    def test_dummy_outcome(self):
        o = Oracle(self.public_key)
        o.load_event_classes(self.event_classes)
        o.print()

        next_event = o._get_next_event_with_time('btceur', self.now + 86400)
        self.assertEqual(next_event['event_id'], 'btceur1763078400')

        event_id = next_event['event_id']
        e1 = o.get_event_by_id(event_id)
        self.assertTrue(e1 != None)
        self.assertEqual(e1['has_outcome'], False)

        # get dummy outcome
        event_outcome = o.dummy_outcome_for_event(event_id)
        self.assert_event_has_outcome(event_outcome)

        # get the event, dummy outcome should not be stored
        e2 = o.get_event_by_id(event_id)
        self.assertEqual(e2['has_outcome'], False)


if __name__ == "__main__":
    unittest.main() # run all tests



