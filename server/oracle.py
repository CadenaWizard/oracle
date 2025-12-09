# Copyright (c) 2025-present Cadena Bitcoin
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

from db import EventStorageDb
import dlcplazacryptlib
from dto import DigitOutcome, EventClassDto, EventDto, Nonce, OutcomeDto
from price import PriceSource
from util import power_of_ten

from datetime import datetime, UTC
from dotenv import load_dotenv
import math
import os
import random
import _thread
import time


# For past events older than this no outcome is genrated
EVENT_TOO_OLD_THRESHOLD=86400

EVENT_STRING_TEMPLATE_DEFAULT = "Outcome:{event_id}:{digit_index}:{digit_outcome}"


# Singleton app instance, created on demand, in get_singleton_instance()
_singleton_app_instance = None

_outcome_loop_thread_started = False


class EventDescription:
    """Common attributes of an event"""

    def __init__(self, definition: str, digits: int, digit_low_pos: int, signer_public_key: str):
        self.definition = definition.upper()
        self.range_digits = digits
        self.range_digit_low_pos = digit_low_pos
        self.signer_public_key = signer_public_key
        # Template for the string for a particular event.
        # Example: "Outcome:{event_id}:{digit_index}:{digit_outcome}"
        self.event_string_template = EVENT_STRING_TEMPLATE_DEFAULT
        # Event type: supported values: 'numeric'
        self.event_type = "numeric"

    def get_minimum_value(self) -> float:
        return 0

    # Compute smallest unit (1, 10, 100, ...) from digit_low_pos (0, 1, 2, ...)
    def get_unit(self) -> int:
        return power_of_ten(self.range_digit_low_pos)

    # Compute high digit pos, from low digit pos and digits
    # E.g. low=0, digits=6 => high=5
    def get_digit_high_pos(self) -> int:
        return self.range_digit_low_pos + self.range_digits - 1

    def get_maximum_value(self) -> float:
        max_val_units = power_of_ten(self.range_digits) - 1
        return max_val_units * self.get_unit()

    def event_string_template_for_id(self, event_id: str) -> str:
        template = self.event_string_template
        return template.replace("{event_id}", event_id)

    # Normalize value into digits, e.g. 85652 -> [0,8,5,6,5]  (5 digits, unit 10.0)
    def value_to_digits(self, value: float) -> list[int]:
        value = float(value)
        min_val = self.get_minimum_value()
        if (value < min_val):
            value = min_val
        if (value > self.get_maximum_value()):
            value = self.get_maximum_value()
        # in the range, check for unit
        unit = self.get_unit()
        if (unit == 0):
            unit = 1
        normalized = round((value - min_val) / unit)
        # convert to digits
        normalized_str = str(normalized)
        n = self.range_digits
        while len(normalized_str) < n:
            normalized_str = '0' + normalized_str
        res = []
        for i in range(n):
            res.append(int(normalized_str[i]))
        return res

    # Convert from digits to actual value, e.g. e.g. [0,8,5,6,5] -> 85650 (5 digits, unit 10.0)
    def digits_to_value(self, digits: list[int]) -> float:
        v = 0
        n = self.range_digits
        for i in range(n):
            v = 10 * v + digits[i]
        value = v * self.get_unit() + self.get_minimum_value()
        return value

    def to_info(self):
        return {
            "definition": self.definition,
            "event_type": self.event_type,
            "range_digits": self.range_digits,
            "range_digit_low_pos": self.range_digit_low_pos,
            "range_digit_high_pos": self.get_digit_high_pos(),
            "range_unit": self.get_unit(),
            "range_min_value": self.get_minimum_value(),
            "range_max_value": self.get_maximum_value(),
            "signer_public_key": self.signer_public_key,
        }


class EventClass:
    """An event class, typically for periodically repeating similar events."""

    def __init__(self, dto: EventClassDto):
        self.dto = dto
        self.desc = EventDescription(definition=dto.definition, digits=dto.range_digits, digit_low_pos=dto.range_digit_low_pos, signer_public_key=dto.signer_public_key)

    # Note: repeat_offset is computed from repeat_first_time, later repeat_first_time should be retired
    def new(id, create_time: int, definition, digits, digit_low_pos, repeat_first_time, repeat_period, repeat_last_time, signer_public_key):
        desc = EventDescription(definition=definition, digits=digits, digit_low_pos=digit_low_pos, signer_public_key=signer_public_key)
        repeat_offset = repeat_first_time % repeat_period
        dto = EventClassDto(
            id=id,
            create_time=create_time,
            definition=desc.definition,
            digits=desc.range_digits,
            digit_low_pos=desc.range_digit_low_pos,
            event_string_template=desc.event_string_template,
            repeat_first_time=repeat_first_time,
            repeat_period=repeat_period,
            repeat_offset=repeat_offset,
            repeat_last_time=repeat_last_time,
            signer_public_key=signer_public_key,
        )
        return EventClass(dto)

    def to_info(self):
        return {
            "class_id": self.dto.id,
            "desc": self.desc.to_info(),
            "repeat_first_time": self.dto.repeat_first_time,
            "repeat_period": self.dto.repeat_period,
            "repeat_offset": self.dto.repeat_offset,
            "repeat_last_time": self.dto.repeat_last_time,
        }

    # Get the next future event time following the given time, 0 on error
    def next_event_time(self, abs_time):
        # print(f"time {self.dto.repeat_first_time} {self.dto.repeat_last_time} {self.dto.repeat_period}  {abs_time}")
        if abs_time > self.dto.repeat_last_time:
            # Out of range
            return 0
        # round up (to nearest second)
        time_adj = int(math.ceil(abs_time))
        # if too early, take first possible
        if time_adj < self.dto.repeat_first_time:
            time_adj = self.dto.repeat_first_time
        # take earlier round-period time (or same)
        time_round_down = int((time_adj - self.dto.repeat_offset) / self.dto.repeat_period) * self.dto.repeat_period + self.dto.repeat_offset
        next_time = time_round_down
        if next_time < abs_time:
            next_time += self.dto.repeat_period
        if next_time > self.dto.repeat_last_time:
            # Would be too late, out of range
            return 0

        assert(next_time >= abs_time)
        assert(next_time >= self.dto.repeat_first_time)
        assert(next_time <= self.dto.repeat_last_time)
        assert(next_time % self.dto.repeat_period == self.dto.repeat_offset)
        return next_time

    # Get the ID of the next future event following the given time, 0 on error
    def next_event_id(self, abs_time):
        next_event_time = self.next_event_time(abs_time)
        if next_event_time == 0:
            return None
        next_event_id = Event.event_id_from_class_and_time(self.dto, next_event_time)
        return next_event_id


class Nonces:
    # Generate nonces. Note: this is a bit slow due to key operations
    def generate(event_id: str, range_digits: int) -> list[Nonce]:
        nonces = []
        for i in range(range_digits):
            # TODO use a non-deterministic, true random nonce here
            newnonce = dlcplazacryptlib.create_deterministic_nonce(event_id, i)
            nonce = Nonce(event_id=event_id, digit_index=i, nonce_pub=newnonce[1], nonce_sec=newnonce[0])
            nonces.append(nonce)
        # print(".", end="")
        return nonces


class Outcome:
    def __init__(self, dto: OutcomeDto, digit_outcomes: list[DigitOutcome]):
        self.dto = dto
        self.digits = digit_outcomes

    # Create the outcome. May throw
    def create(outcome_value: str, event_id: str, event_desc: EventDescription, created_time: float, signer_public_key: str, nonces: list[Nonce]):
        outcome_dto = OutcomeDto(event_id=event_id, value=outcome_value, created_time=created_time)

        digit_values = event_desc.value_to_digits(float(outcome_value))
        # the number of digits, nonces, signatures
        n = event_desc.range_digits
        # check that digit_values[], nonces.n[] have enough elements
        if len(digit_values) < n:
            raise Exception(f"Not enough digit_values, {digit_values} {n}")
        if len(nonces) < n:
            raise Exception(f"Not enough nonces, {len(nonces)} {n}")

        # For signing we use the pubkey configured into cryptlib,
        # Check that signer pubkey matches the event's
        lib_pubkey = dlcplazacryptlib.get_public_key(0)
        if lib_pubkey != signer_public_key:
            raise Exception(f"Signing error: key not matching pubkey '{signer_public_key}' ({lib_pubkey})")

        digits = []
        for i in range(n):
            msg = Outcome.string_for_event(event_desc, event_id, i, digit_values[i])
            sig = dlcplazacryptlib.sign_schnorr_with_nonce(msg, nonces[i].nonce_sec, 0)
            digit_outcome = DigitOutcome(event_id, i, digit_values[i], nonces[i].nonce_pub, sig, msg)
            digits.append(digit_outcome)
        return Outcome(dto=outcome_dto, digit_outcomes=digits)

    def string_for_event(event_desc: EventDescription, event_id: str, digit_index: int, digit_outcome: int) -> str:
        s = event_desc.event_string_template_for_id(event_id)
        s = s.replace("{digit_index}", str(digit_index))
        s = s.replace("{digit_outcome}", str(digit_outcome))
        return s


class Event:
    """An individual event"""

    def __init__(self, dto: EventDto, desc: EventDescription, event_class_id: str, signer_public_key: str):
        self.dto = dto
        self.desc = desc
        self.event_class_id = event_class_id
        self.signer_public_key = signer_public_key

    def new(time, event_class: EventClass):
        assert(event_class is not None)
        event_id = Event.event_id_from_class_and_time(event_class.dto, time)
        class_id = event_class.dto.id
        string_template = event_class.desc.event_string_template_for_id(event_id)
        event_dto = EventDto(event_id=event_id, class_id=class_id, definition=event_class.dto.definition, time=time, string_template=string_template, signer_public_key_id=-1)
        return Event(event_dto, event_class.desc, class_id, signer_public_key=event_class.dto.signer_public_key)

    # Construct event ID of the form 'btceur1748991600'
    def event_id_from_class_and_time(event_class_dto: EventClassDto, time):
        return event_class_dto.definition.lower() + str(time)


class Oracle:
    def __init__(self, public_key, data_dir_override: str = None, price_source_override = None):
        load_dotenv()
        # DB dir, from .env, or override
        data_dir = None
        if data_dir_override is not None:
            data_dir = data_dir_override
        else:
            data_dir = os.getenv("DB_DIR", ".")

        # Horizon, from dotenv
        self.horizon_days = float(os.getenv("HORIZON_DAYS", 390))
        print(f"Horizon setting: {self.horizon_days} days")

        if price_source_override is None:
            price_source = PriceSource()
        else:
            price_source = price_source_override
        self.db = EventStorageDb(data_dir=data_dir)
        self.public_key = public_key
        self.price_source = price_source

    def initialize_cryptlib() -> str:
        # Take location of secret file from dotenv
        load_dotenv()
        secret_file = os.getenv("KEY_SECRET_FILE_NAME", default="./secret.sec")
        secret_pass = os.getenv("KEY_SECRET_PWD", default="")

        _xpub = dlcplazacryptlib.init(secret_file, secret_pass)
        public_key = dlcplazacryptlib.get_public_key(0)
        print("dlcplazacryptlib initialized, public key:", public_key)
        return public_key

    def close(self):
        self.db.close()

    def delete_all_contents(self):
        self.db.delete_all_contents()

    def load_event_classes(self, event_classes, defer_nonces = False):
        for ec in event_classes:
            self.add_event_class_and_events(ec, defer_nonces=defer_nonces)

    def add_event_class_and_events(self, ec: EventClass, defer_nonces = False):
        print(f"Generating events for event class '{ec.dto.id}' '{ec.dto.definition}' ...")
        inserted = self.db.event_classes_insert_if_missing(ec.dto)
        if inserted == 0:
            print(f"ERROR: Event class already present! id '{ec.dto.id}'")
            return
        event_dtos, nonces = self.generate_events_from_class(ec=ec, defer_nonces=defer_nonces)
        print(f"add_event_class_and_events Generated {len(event_dtos)} events and {len(nonces)} nonces (in memory)")
        added_event_cnt = self.db.events_append_if_missing(event_dtos, ec.dto.signer_public_key)
        if len(nonces) > 0:
            self.db.nonces_insert(nonces)
        print(f"Loaded event class '{ec.dto.id}', generated {len(event_dtos)} events, inserted {added_event_cnt}, total {self.db.events_len()}")
        self.db.print_stats()

    def print_stats(self):
        self.db.print_stats()
        now = round(datetime.now(UTC).timestamp())
        print(f"Oracle, with {self.db.events_count_future(now)} future events ({self.db.events_len()} total), and {self.db.event_classes_len()} eventclasses")

    # Generate events. Also nonces, unless deferred
    def generate_events_from_class(self, ec: EventClass, defer_nonces = False) -> tuple[list[EventDto], list[Nonce]]:
        events = []
        noncess = []
        t = ec.dto.repeat_first_time
        cnt = 0
        assert(ec.dto.repeat_period != 0)
        while t <= ec.dto.repeat_last_time:
            assert(t % ec.dto.repeat_period == ec.dto.repeat_offset)
            # create event
            ev = Event.new(event_class=ec, time=t)
            # eid = ev.dto.event_id
            # print(cnt, " ", eid, ", ", ev.time, ' ', ev.desc.range_digits)
            events.append(ev.dto)

            if not defer_nonces:
                nonces1 = self.generate_nonces(ev)
                for n in nonces1:
                    noncess.append(n)
                if len(noncess) % 10 == 0:
                    print(".", end='')
                if len(noncess) % 1000 == 0:
                    print(f"\n{len(noncess)}")
            t += ec.dto.repeat_period
            cnt += 1
        return (events, noncess)

    # Note: public keys may be extended to several
    def get_oracle_info(self):
        return {
            "main_public_key": self.public_key,
            "public_keys": [ self.public_key ],
        }

    def _get_oracle_status_time(self, current_time: float):
        future_count = self.db.events_count_future(current_time)
        return {
            "future_event_count": future_count,
            "total_event_count": self.db.events_len(),
            "current_time_utc": round(current_time, 3)
        }

    def get_oracle_status(self):
        now = datetime.now(UTC).timestamp()
        return self._get_oracle_status_time(now)

    def compute_event_time_range(repeat_period: int, repeat_offset: int, start_time: int, end_time: int) -> tuple[int, int]:
        assert(repeat_period != 0)
        first_time = math.floor((start_time - repeat_offset) / repeat_period) * repeat_period + repeat_offset
        last_time = math.ceil((end_time - repeat_offset) / repeat_period) * repeat_period + repeat_offset
        assert(first_time <= start_time)
        assert(last_time >= end_time)
        assert(first_time <= last_time)
        assert((first_time - repeat_offset) % repeat_period == 0)
        assert((last_time - repeat_offset) % repeat_period == 0)
        return [first_time, last_time]

    def create_event_class(self, class_id: str, definition: str, digits: int, digit_low_pos: int, repeat_period, repeat_offset, public_key: str, now: int) -> EventClass:
        horizon = now + self.horizon_days * 86400
        first_time, last_time = Oracle.compute_event_time_range(repeat_period=repeat_period, repeat_offset=repeat_offset, start_time=now, end_time=horizon)
        return EventClass.new(class_id, now, definition.upper(), digits, digit_low_pos, first_time, repeat_period, last_time, public_key)

    # TODO: such operational data should be moved out of code, into config/DB
    def initialize_with_default_data(self, public_key):
        self.db.delete_all_contents()
        self.db.print_stats()
        now = round(datetime.now(UTC).timestamp())

        ec1 = self.create_event_class(class_id="btcusd", definition="BTCUSD", digits=7, digit_low_pos=0, repeat_period=10*60, repeat_offset=0, public_key=public_key, now=now)
        ec2 = self.create_event_class(class_id="btceur", definition="BTCEUR", digits=7, digit_low_pos=0, repeat_period=12*3600, repeat_offset=0, public_key=public_key, now=now)
        default_event_classes=[ec1, ec2]

        # TODO: No need to defer nonces, once they are in created only at DB creation
        self.load_event_classes(default_event_classes, defer_nonces=True)
        self.print_stats()

    def get_default_instance(data_dir_override = None):
        public_key = Oracle.initialize_cryptlib()
        o = Oracle(public_key=public_key, data_dir_override=data_dir_override)
        # Note: Do NOT reinitialize DB, use persisted
        return o

    # Get event classes
    def get_event_classes(self):
        return list(map(lambda ec: EventClass(ec).to_info(), self.db.event_classes_get_all()))

    def get_event_class_latest_by_def(self, definition: str) -> EventClass:
        if not definition:
            return None
        def_upper = definition.upper()
        dto = self.db.event_classes_get_latest_by_def(def_upper)
        if dto == None:
            return None
        return EventClass(dto)

    # In case there are more, return all
    def get_event_classes_by_def(self, definition: str) -> list[EventClass]:
        if not definition:
            return None
        def_upper = definition.upper()
        dtos = self.db.event_classes_get_all_by_def(def_upper)
        return list(map(lambda dto: EventClass(dto), dtos))

    # Generate nonces for an event
    def generate_nonces(self, e: Event):
        nonces = Nonces.generate(e.dto.event_id, e.desc.range_digits)
        assert(len(nonces) > 0)
        return nonces

    # Generate nonces for an event, and insert them in DB
    def generate_and_insert_nonces(self, e: Event):
        nonces = self.generate_nonces(e)
        self.db.nonces_insert(nonces)
        nonces = self.db.nonces_get(e.dto.event_id)
        assert(len(nonces) > 0)
        # print(f"Nonces inserted, {e.dto.event_id} {len(nonces)}")
        return nonces

    # Access nonces, Fill on-demand
    def get_nonces(self, event: Event) -> list[Nonce]:
        eid = event.dto.event_id
        nonces = self.db.nonces_get(eid)
        if len(nonces) > 0:
            # There are nonces
            return nonces
        # No nonces, generate now!
        return self.generate_and_insert_nonces(event)

    def get_outcome(self, event_id: str) -> Outcome | None:
        # get outcome (if any)
        outcome_dto = self.db.outcomes_get(event_id)
        if outcome_dto is None:
            return None
        digits = self.db.digitoutcomes_get(event_id)
        return Outcome(outcome_dto, digits)

    def _get_event_info_with_outcome(self, event: Event, override_outcome: Outcome | None):
        if override_outcome is None:
            outcome = self.get_outcome(event.dto.event_id)
        else:
            outcome = override_outcome

        has_outcome = (outcome is not None)
        nonces = self.get_nonces(event)
        info = {
            "event_id": event.dto.event_id,
            "time_utc": event.dto.time,
            "time_utc_nice": str(datetime.fromtimestamp(event.dto.time, UTC)),
            "definition": event.desc.definition,
            "event_type": event.desc.event_type,
            "range_digits": event.desc.range_digits,
            "range_digit_low_pos": event.desc.range_digit_low_pos,
            "range_digit_high_pos": event.desc.get_digit_high_pos(),
            "range_unit": event.desc.get_unit(),
            "range_min_value": event.desc.get_minimum_value(),
            "range_max_value": event.desc.get_maximum_value(),
            "event_class": event.event_class_id,
            "signer_public_key": event.desc.signer_public_key,
            "string_template": event.dto.string_template,
            "has_outcome": has_outcome,
            # public nonces
            "nonces": list(map(lambda n: n.nonce_pub, nonces)),
        }
        if has_outcome:
            info["outcome_value"] = outcome.dto.value
            info["outcome_time"] = outcome.dto.created_time
            info["digits"] = list(map(lambda di: di.to_info(), outcome.digits))
        return info

    def get_event_info(self, event: Event):
        return self._get_event_info_with_outcome(event, None)

    def get_event_obj_by_id(self, event_id: str) -> Event | None:
        res = self.db.events_get_by_id(event_id)
        if res is None:
            return None
        e_dto, pubkey = res
        event_class_dto = self.db.event_classes_get_by_id(e_dto.class_id)
        if event_class_dto is None:
            # Could not get event class!
            return None
        desc = EventClass(event_class_dto).desc
        return Event(e_dto, desc, event_class_dto.id, pubkey)

    def get_event_by_id(self, event_id: str):
        e = self.get_event_obj_by_id(event_id)
        if e is None:
            return {}
        return self._get_event_info_with_outcome(e, None)

    # Note: Max count is capped at the hard limit of 100 events, to prevent large responses
    def get_events_filter(self, start_time: int = 0, end_time = 0, definition: str = None, max_count: int = 100) -> list[dict]:
        if definition is not None:
            definition = definition.upper()
        max_count_hard_limit = 100
        max_count = min(max_count, max_count_hard_limit)
        event_ids = self.db.events_get_ids_filter(start_time, end_time, definition, max_count)
        event_infos = list(map(lambda eid: self.get_event_by_id(eid), event_ids))
        return event_infos

    # Note: a hard limit of 5000 limit is applied, to prevent very large responses
    def get_event_ids_filter(self, start_time: int = 0, end_time = 0, definition: str = None) -> list[str]:
        if definition is not None:
            definition = definition.upper()
        return self.db.events_get_ids_filter(start_time, end_time, definition, 5000)

    # Get the ID of the next event for a definition, after the given time
    def _get_next_event_id_with_time(self, definition: str, abs_time: float) -> int:
        # In case of multiple classes, try all of them, as we don't know whose time period matches the requested
        event_classes = self.get_event_classes_by_def(definition)
        for ec in event_classes:
            next_event_id = ec.next_event_id(abs_time)
            # print(f"next_event_id {next_event_id}")
            if next_event_id is not None:
                return next_event_id
        # None found
        return None

    # Get the next instance of an event class, after the given time
    def _get_next_event_with_time(self, definition: str, abs_time: float) -> dict:
        next_event_id = self._get_next_event_id_with_time(definition, abs_time)
        if not next_event_id:
            return {}

        event = self.get_event_obj_by_id(next_event_id)
        if not event:
            return {}
        assert(event.dto.time >= abs_time)
        return self.get_event_info(event)

    # Get the next instance of an event class, after the given time
    def get_next_event(self, definition: str, period: int = 60) -> dict:
        period_cap = max(period, 60)
        abs_time = math.ceil(datetime.now(UTC).timestamp()) + period_cap
        return self._get_next_event_with_time(definition, abs_time)

    def get_price(self, symbol, pref_max_age: float):
        return self.price_source.get_price_info(symbol, pref_max_age=pref_max_age).price

    # Return the number of events modified, and the next time due
    def _create_past_outcomes_time(self, current_time: float, event_too_old_threshold: int = 86400) -> tuple[int, int]:
        cnt = 0
        # past events without outcome
        past_events = self.db.events_get_past_no_outcome(current_time)
        if len(past_events) == 0:
            return (0, self.db.events_get_earliest_time_without_outcome(current_time))

        # Filter out VERY old events
        if event_too_old_threshold == 0:
            events = past_events
        else:
            too_old_time = math.ceil(current_time - event_too_old_threshold)
            cnt_too_old = 0
            events = []
            for eid in past_events:
                e = self.get_event_obj_by_id(eid)
                if e is None:
                    continue
                if e.dto.time >= too_old_time:
                    events.append(e)
                else:
                    cnt_too_old += 1
            if cnt_too_old > -0:
                print(f"WARNING: There are {cnt_too_old} events that are too old and have no outcome! {event_too_old_threshold} {len(events)}")

        if len(events) == 0:
            return (0, self.db.events_get_earliest_time_without_outcome(current_time))
        print(f"Found {len(events)} past events that need outcome")
        for e in events:
            symbol = e.desc.definition
            value = self.get_price(symbol, pref_max_age=15)
            try:
                outcome = Outcome.create(str(value), e.dto.event_id, e.desc, current_time, e.signer_public_key, self.get_nonces(e))
                self.db.digitoutcomes_insert(e.dto.event_id, outcome.digits)
                self.db.outcomes_insert(outcome.dto)
            except Exception as ex:
                print(f"EXCEPTION while creating outcome, {ex}")
                # continue
            cnt += 1
        if cnt == 0:
            return (0, self.db.events_get_earliest_time_without_outcome(current_time))
        print(f"Created outcomes for {cnt} past events")
        self.print_stats()
        return (cnt, self.db.events_get_earliest_time_without_outcome(current_time))

    def create_past_outcomes(self) -> int:
        now = datetime.now(UTC).timestamp()
        # print("Checking for past outcome generation ...", round(now))
        return self._create_past_outcomes_time(now, event_too_old_threshold=EVENT_TOO_OLD_THRESHOLD)

    # Return the number of events modified, and the next time due
    def _create_future_events(self, current_time_orig: float, max_count = 10) -> tuple[int, int]:
        ct = math.floor(current_time_orig)
        horizon = ct + self.horizon_days * 86400

        # Go by event classes
        cnt = 0
        earliest_next_event = 0
        for ec in self.db.event_classes_get_all():
            look_from = self.db.events_get_latest_time_for_def(ec.definition)
            # print(look_from, look_from - ct)
            if look_from == 0 or look_from is None:
                look_from = ct
            _ft, last_time = Oracle.compute_event_time_range(repeat_period=ec.repeat_period, repeat_offset=ec.repeat_offset, start_time=look_from, end_time=horizon)
            # print(f"Checking range {_ft} -- {last_time}  {last_time - _ft}  {(last_time - _ft)/ec.repeat_period}  {ec.definition}")
            # Iterate over times, check if event exists
            t = _ft
            while t <= last_time:
                # Check if event exists
                event_id = Event.event_id_from_class_and_time(ec, t)
                e = self.db.events_get_by_id(event_id)
                if e is None:
                    print(f"Need to generate future event for '{ec.definition}' time {t} {t - ct}")
                    assert(t % ec.repeat_period == ec.repeat_offset)
                    # create event, also nonces
                    try:
                        ev = Event.new(event_class=EventClass(ec), time=t)
                        assert(ev is not None)
                        self.db.events_insert_if_missing(ev.dto, ec.signer_public_key)
                        nonces = self.generate_and_insert_nonces(ev)
                        assert(len(nonces) > 0)
                    except Exception as ex:
                        print(f"EXCEPTION while creating outcome, {ex}")
                    cnt+=1
                    if cnt >= max_count:
                        break
                else:
                    # this time slot is filled
                    next = t + ec.repeat_period
                    if earliest_next_event == 0:
                        earliest_next_event = next
                    else:
                        earliest_next_event = min(earliest_next_event, next)
                t += ec.repeat_period
            if cnt >= max_count:
                break
        # print(f"Future event check done, {cnt}")
        if cnt > 0:
            print(f"Generated {cnt} new future events")
            self.print_stats()
        return (cnt, earliest_next_event)

    def create_future_events(self, max_count = 10) -> int:
        now = datetime.now(UTC).timestamp()
        return self._create_future_events(now, max_count=max_count)

    def create_nonces(self, max_count = 100) -> int:
        eids = self.db.events_get_ids_with_no_nonce(limit=max_count)
        if len(eids) == 0:
            return 0
        # print(f"WARNING: Found at least {len(eids)} events with no nonces! Filling...")
        cnt = 0
        for eid in eids:
            e = self.get_event_obj_by_id(eid)
            if e is None:
                continue
            nonces = self.get_nonces(e)
            assert(len(nonces) > 0)
            cnt += 1
            if cnt >= max_count:
                break
        if cnt > 0:
            print(f"Touched nonces for {cnt} events...")
            self.db.print_stats()
        return cnt


    # def dummy_outcome_for_event(self, event_id):
    #     e = self.get_event_obj_by_id(event_id)
    #     if e == None:
    #         return {}
    #     if self.db.outcomes_exists(event_id):
    #         # already has outcome
    #         return self.get_event_info(e)
    #     # has no outcome yet
    #     symbol = e.desc.definition
    #     value = self.get_price(symbol, e.dto.time)
    #     now = datetime.now(UTC).timestamp()
    #     try:
    #         outcome = Outcome.create(str(value), e.dto.event_id, e.desc, now, self.get_nonces(e))
    #         return self._get_event_info_with_outcome(e, outcome)
    #     except Exception as ex:
    #         print(f"Exception while generating dummy outcome, {ex}")
    #         return {}

    # Continuously check for:
    # - events that has just became due and outcome is needed
    # - new events that need to be generated at the expanding horizon
    def check_outcome_loop(self, early_exit = False):
        print("check_outcome_loop started", round(datetime.now(UTC).timestamp()))
        while True:
            cnt, next1 = self.create_past_outcomes()
            if cnt > 0:
                continue

            cnt, next2 = self.create_future_events(10)
            if cnt > 0:
                continue

            if early_exit:
                print("check_outcome_loop: all is fine, exiting")
                break

            # Wait some
            next = next1
            if next == 0:
                next = next2
            else:
                if next2 != 0 and next2 < next:
                    next = next2
            # print(next1, next2, next)
            now = datetime.now(UTC).timestamp()
            towait_unbound = (next - now) / 2 - 1
            towait = min(max(towait_unbound, 0.01), 60)
            # print(next1, next2, next, now, towait_unbound, towait)
            if towait > 0.5:
                print(f"Sleeping for {round(towait, 3)} s (of {round(towait_unbound, 1)}) ...")
            time.sleep(towait)
            # print(" ")


    # Fill all event nonces, some may be missing (deferred)
    def fill_nonces_all(self):
        eids = self.db.events_get_ids_with_no_nonce(limit=10)
        if len(eids) > 0:
            print(f"WARNING: Found events with no nonces! Filling...")
        while True:
            c = self.create_nonces(1000)
            if c == 0:
                # None updated, stop
                print("No nonces to fill, OK")
                break
            time.sleep(0.1)
            continue


class OracleApp:
    oracle: Oracle

    def __init__(self, data_dir_override = None):
        self.oracle = Oracle.get_default_instance(data_dir_override=data_dir_override)
        random.seed()
        self.oracle.print_stats()
        print("OracleApp instance created")

    def get_singleton_instance() -> Oracle:
        print("get_singleton_instance")
        global _singleton_app_instance
        if not _singleton_app_instance:
            _singleton_app_instance = OracleApp.create_default_app_instance()
        return _singleton_app_instance

    def create_default_app_instance() -> Oracle:
        app = OracleApp(data_dir_override=None)
        global _outcome_loop_thread_started
        if not _outcome_loop_thread_started:
            _thread.start_new(outcome_loop_thread, (app.oracle,))
            _thread.start_new(nonce_loop_thread, (app.oracle,))
        return app

    def get_oracle(self):
        return self.oracle

    def get_current_price(self, symbol: str):
        value = self.oracle.price_source.get_price_info(symbol, pref_max_age=60).price
        return value

    def get_current_prices(self):
        res = {}
        for symbol in self.oracle.price_source.get_symbols():
            value = self.oracle.price_source.get_price_info(symbol, pref_max_age=60).price
            res[symbol] = value
        return res

    def get_current_price_info(self, symbol: str):
        info = self.oracle.price_source.get_price_info(symbol, pref_max_age=60)
        return info

    def get_current_price_infos(self):
        res = {}
        for symbol in self.oracle.price_source.get_symbols():
            info = self.oracle.price_source.get_price_info(symbol, pref_max_age=60)
            res[symbol] = info
        return res

def outcome_loop_thread(oracle):
    global _outcome_loop_thread_started
    _outcome_loop_thread_started = True
    time.sleep(1)
    oracle.check_outcome_loop(early_exit=False)

def nonce_loop_thread(oracle):
    time.sleep(10)
    oracle.fill_nonces_all()

