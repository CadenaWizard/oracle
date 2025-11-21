from db import EventStorageDb
from dto import EventClassDto, EventDto, DigitOutcome, Nonce, OutcomeDto
from test_common import recreate_empty_db_file

import math
import unittest


class EventStorageTestClass(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        print("setUpClass")
        cls.digits = 7
        time = 1763000000
        cls.start_time = time
        repeat_time = 3600
        repeat_first_time = int(math.floor(time / repeat_time)) * repeat_time - 7 * repeat_time
        repeat_last_time = repeat_first_time + 37 * repeat_time
        cls.default_event_class = EventClassDto("btcusd01", time, "BTCUSD", cls.digits, 0, "Outcome:{event_id}:{digit_index}:{digit_outcome}", repeat_first_time, repeat_time, 0, repeat_last_time, "signer_pubkey_001")

    # Helper to create storage instance
    def create_db(self):
        recreate_empty_db_file()

        db = EventStorageDb(data_dir=".")
        return db

    def test_init(self):
        db = self.create_db()
        db.print_stats()
        self.assertEqual(db.event_classes_len(), 0)
        self.assertEqual(db.events_len(), 0)

    def test_add_some(self):
        db = self.create_db()
        db.print_stats()

        # Prepare an event class
        event_class = self.default_event_class
        db.event_classes_insert_if_missing(event_class)

        # Ask back
        self.assertEqual(db.event_classes_len(), 1)
        self.assertEqual(db.event_classes_get_by_id(event_class.id).__dict__, event_class.__dict__)

        # Try to add again
        db.event_classes_insert_if_missing(event_class)
        self.assertEqual(db.event_classes_len(), 1)

        # Prepare some events
        EVENTS_NUM=5
        for i in range(EVENTS_NUM):
            period = 5 + i
            time = event_class.repeat_first_time + period * event_class.repeat_period
            event_id = "ev_btcusd_01_00" + str(period)
            template = event_class.event_string_template.replace("{event_id}", event_id)
            e = EventDto(event_id, class_id=event_class.id, definition=event_class.definition, time=time, string_template=template, signer_public_key_id=-1)
            db.events_insert_if_missing(e, "signer_pubkey_001")

            # Ask back
            self.assertEqual(db.events_len(), i + 1)
            evb, spb = db.events_get_by_id(event_id)
            self.assertEqual(evb.__dict__, e.__dict__)
            self.assertEqual(evb.string_template, "Outcome:ev_btcusd_01_00" + str(period) + ":{digit_index}:{digit_outcome}")
            self.assertEqual(spb, "signer_pubkey_001")

            # Try to add again
            db.events_insert_if_missing(e,"signer_pubkey_001")
            self.assertEqual(db.events_len(), i + 1)

            # Prepare some nonces
            nonces = []
            for d in range(event_class.range_digits):
                nonces.append(Nonce(event_id, digit_index=d, nonce_pub=f"nonce_pub_00_{period}_{d}", nonce_sec=f"nonce_SEC_00_{period}_{d}"))
            db.nonces_insert(nonces)

            # Ask back
            nonces_back = db.nonces_get(event_id)
            self.assertEqual(len(nonces_back), event_class.range_digits)
            self.assertEqual(nonces_back[3].digit_index, 3)

        # Now prepare outcomes
        for i in range(EVENTS_NUM):
            period = 5 + i
            event_id = "ev_btcusd_01_00" + str(period)
            value = 100000 + i * 1000
            outcome_time = event_class.repeat_first_time + 20 * event_class.repeat_period + 3
            o = OutcomeDto(event_id, value=value, created_time=outcome_time)
            db.outcomes_insert(o)

            # Prepare digitoutcomes
            nonces = db.nonces_get(event_id)
            dos = []
            for d in range(event_class.range_digits):
                event, _spk = db.events_get_by_id(event_id)
                digit_value = int(("0"+str(value))[d])
                msg_str = event.string_template.replace("{digit_index}", str(d)).replace("{digit_outcome}", str(digit_value))
                do = DigitOutcome(event_id, index=d, value=digit_value, nonce=nonces[d].nonce_pub, signature=f"This_is_a_signature_{event_id}_{d}", msg_str=msg_str)
                # print(do.__dict__)
                dos.append(do)
            db.digitoutcomes_insert(event_id, dos)

            # Ask back
            dos_back = db.digitoutcomes_get(event_id)
            self.assertEqual(len(dos_back), event_class.range_digits)
            self.assertEqual(dos_back[3].index, 3)
            expected_digit_outcome = int(("0"+str(value))[3])
            self.assertEqual(dos_back[3].msg_str, "Outcome:ev_btcusd_01_00" + str(period) + ":3:" + str(expected_digit_outcome))

        db.print_stats()


    def test_add_some_invalid_references(self):
        db = self.create_db()
        db.print_stats()

        event_class_id = "btcusd_class01"
        event_id = "ev_btcusd_02_007"

        # make sure event class does not exit
        self.assertIsNone(db.event_classes_get_by_id(event_class_id))
        # make sure event does not exit
        self.assertIsNone(db.events_get_by_id(event_id))

        o = OutcomeDto(event_id, 99999, self.start_time)
        self.assertRaises(Exception, db.outcomes_insert, (o,))
        self.assertIsNone(db.outcomes_get(event_id))

        do = DigitOutcome(event_id, 3, 7, "nonce", "sig", "msg_str")
        self.assertRaises(Exception, db.digitoutcomes_insert, (event_id, [do]))
        self.assertEqual(len(db.digitoutcomes_get(event_id)), 0)

        nonces = Nonce(event_id, 3, "nonce_pubkey", "nonce_seckey")
        self.assertRaises(Exception, db.nonces_insert, ([nonces],))
        self.assertEqual(len(db.nonces_get(event_id)), 0)

        e = EventDto(event_id=event_id, class_id=event_class_id, definition="BTCUSD", time=self.start_time, string_template="template", signer_public_key_id=-1)
        self.assertRaises(Exception, db.events_insert_if_missing, (e, "signer_pubkey"))
        self.assertIsNone(db.events_get_by_id(event_id))

        # Event class has no dependency
        repeat_time = 3600
        repeat_first_time = int(math.floor(self.start_time / repeat_time)) * repeat_time - 7 * repeat_time
        repeat_last_time = repeat_first_time + 37 * repeat_time
        ec = EventClassDto(
            id=event_class_id, create_time=self.start_time, definition="BTCUSD", digits=7, digit_low_pos=0, event_string_template="template",
            repeat_first_time=repeat_first_time, repeat_period=repeat_time, repeat_offset=0, repeat_last_time=repeat_last_time, signer_public_key="signer_pubkey"
        )
        db.event_classes_insert_if_missing(ec)
        self.assertIsNotNone(db.event_classes_get_by_id(event_class_id))
        self.assertEqual(db.event_classes_get_by_id(event_class_id).id, event_class_id)

        # Event can go now
        db.events_insert_if_missing(e, "signer_pubkey")
        self.assertEqual(
            db.events_get_by_id(event_id)[0].__dict__,
            {'class_id': 'btcusd_class01', 'definition': 'BTCUSD', 'event_id': 'ev_btcusd_02_007', 'signer_public_key_id': 1, 'string_template': 'template', 'time': 1763000000}
        )

        # nonces can go now
        db.nonces_insert([nonces])
        self.assertEqual(len(db.nonces_get(event_id)), 1)
        self.assertEqual(
            db.nonces_get(event_id)[0].__dict__,
            {'digit_index': 3, 'event_id': 'ev_btcusd_02_007', 'nonce_pub': 'nonce_pubkey', 'nonce_sec': 'nonce_seckey'}
        )

        # digit outcome can go now
        db.digitoutcomes_insert(event_id, [do])
        self.assertEqual(len(db.digitoutcomes_get(event_id)), 1)

        # outcome can go now
        db.outcomes_insert(o)
        self.assertIsNotNone(db.outcomes_get(event_id))

        db.print_stats()


    def test_get_event_by_outcome(self):
        db = self.create_db()
        db.print_stats()

        # Prepare an event class
        event_class = self.default_event_class
        db.event_classes_insert_if_missing(event_class)
        self.assertEqual(db.event_classes_len(), 1)

        # Prepare some events
        EVENTS_NUM=6
        events = []
        for i in range(EVENTS_NUM):
            period = 5 + i
            time = event_class.repeat_first_time + period * event_class.repeat_period
            event_id = "ev_btcusd_01_00" + str(period)
            template = event_class.event_string_template.replace("{event_id}", event_id)
            e = EventDto(event_id, class_id=event_class.id, definition=event_class.definition, time=time, string_template=template, signer_public_key_id=-1)
            events.append(e)
            db.events_insert_if_missing(e, "signer_pubkey_001")

            # Prepare some nonces
            nonces = []
            for d in range(event_class.range_digits):
                nonces.append(Nonce(event_id, digit_index=d, nonce_pub=f"nonce_pub_00_{period}_{d}", nonce_sec=f"nonce_SEC_00_{period}_{d}"))
            db.nonces_insert(nonces)

        self.assertEqual(db.events_len(), 6)

        # Prepare outcome for the first 3
        for i in range(3):
            period = 5 + i
            event_id = "ev_btcusd_01_00" + str(period)
            value = 100000 + i * 1000
            outcome_time = event_class.repeat_first_time + 20 * event_class.repeat_period + 3
            o = OutcomeDto(event_id, value=value, created_time=outcome_time)
            db.outcomes_insert(o)

            # Prepare digitoutcomes
            nonces = db.nonces_get(event_id)
            dos = []
            for d in range(event_class.range_digits):
                event, _spk = db.events_get_by_id(event_id)
                digit_value = int(("0"+str(value))[d])
                msg_str = event.string_template.replace("{digit_index}", str(d)).replace("{digit_outcome}", str(digit_value))
                do = DigitOutcome(event_id, index=d, value=digit_value, nonce=nonces[d].nonce_pub, signature=f"This_is_a_signature_{event_id}_{d}", msg_str=msg_str)
                # print(do.__dict__)
                dos.append(do)
            db.digitoutcomes_insert(event_id, dos)

        earliest_time = db.events_get_earliest_time_without_outcome()
        self.assertEqual(earliest_time, 1763002800)

        self.assertEqual(db.events_get_past_no_outcome(events[5].time + 1000), ["ev_btcusd_01_008", "ev_btcusd_01_009", "ev_btcusd_01_0010"])
        self.assertEqual(db.events_get_past_no_outcome(events[4].time + 1000), ["ev_btcusd_01_008", "ev_btcusd_01_009"])
        self.assertEqual(db.events_get_past_no_outcome(events[3].time + 1000), ["ev_btcusd_01_008"])

        self.assertEqual(db.events_count_future(events[5].time - 1000), 1)
        self.assertEqual(db.events_count_future(events[4].time - 1000), 2)
        self.assertEqual(db.events_count_future(events[3].time - 1000), 3)

        self.assertEqual(len(db.events_get_ids_filter(
            events[1].time - 1000,
            events[5].time + 1000,
            None, 1000
        )), 5)
        self.assertEqual(len(db.events_get_ids_filter(
            events[2].time - 1000,
            events[4].time + 1000,
            None, 1000
        )), 3)
        self.assertEqual(len(db.events_get_ids_filter(
            events[2].time - 1000,
            events[4].time + 1000,
            "BTCUSD", 1000
        )), 3)
        self.assertEqual(len(db.events_get_ids_filter(
            events[2].time - 1000,
            events[4].time + 1000,
            "BTCEUR", 1000
        )), 0)
        self.assertEqual(len(db.events_get_ids_filter(
            events[1].time - 1000,
            events[5].time + 1000,
            "BTCUSD", 2
        )), 2)

        db.print_stats()


if __name__ == "__main__":
    unittest.main() # run all tests

