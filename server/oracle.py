# Copyright (c) 2025-present Cadena Bitcoin
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

import dlcplazacryptlib
from dto import DigitOutcome, EventClassDto, EventDto, Nonce, OutcomeDto
from price import PriceSource
from util import power_of_ten

from datetime import datetime, UTC
import copy
import math
import random
import sys
import _thread
import time


EVENT_STRING_TEMPLATE_DEFAULT = "Outcome:{event_id}:{digit_index}:{digit_outcome}"


# Singleton app instance, created on demand, in _get_singleton_instance()
_singleton_app_instance = None

_outcome_loop_thread_started = False


class EventDescription:
    """Common attributes of an event"""

    def __init__(self, definition: str, digits: int, digit_low_pos: int):
        self.definition = definition.upper()
        self.range_digits = digits
        self.range_digit_low_pos = digit_low_pos
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
        }


class EventClass:
    """An event class, typically for periodically repeating similar events."""

    def __init__(self, dto: EventClassDto):
        self.dto = dto
        self.desc = EventDescription(definition=dto.definition, digits=dto.range_digits, digit_low_pos=dto.range_digit_low_pos)

    def new(id, definition, digits, digit_low_pos, repeat_first_time, repeat_period, repeat_last_time):
        descirption = EventDescription(definition=definition, digits=digits, digit_low_pos=digit_low_pos)
        dto = EventClassDto(
            id=id,
            definition=descirption.definition,
            digits=descirption.range_digits,
            digit_low_pos=descirption.range_digit_low_pos,
            event_string_template=descirption.event_string_template,
            repeat_first_time=repeat_first_time,
            repeat_period=repeat_period,
            repeat_last_time=repeat_last_time
        )
        return EventClass(dto)

    def to_info(self):
        return {
            "class_id": self.dto.id,
            "desc": self.desc.to_info(),
            "repeat_first_time": self.dto.repeat_first_time,
            "repeat_period": self.dto.repeat_period,
            "repeat_last_time": self.dto.repeat_last_time,
        }

    # Get the next future event time following the given time, 0 on error
    def next_event_time(self, abs_time):
        # print("time", self.repeat_first_time, self.repeat_last_time, self.repeat_period, time)
        if abs_time > self.dto.repeat_last_time:
            # Out of range
            return 0
        time_adj = max(self.dto.repeat_first_time, abs_time)
        period_count = int(math.floor((int(time_adj) - 1 - self.dto.repeat_first_time) / self.dto.repeat_period)) + 1
        next_time = self.dto.repeat_first_time + period_count * self.dto.repeat_period
        if next_time > self.dto.repeat_last_time:
            # Would be too late, out of range
            return 0
        assert(next_time >= abs_time)
        assert(next_time >= self.dto.repeat_first_time)
        assert(next_time <= self.dto.repeat_last_time)
        return next_time

    # Get the ID of the next future event following the given time, 0 on error
    def next_event_id(self, abs_time):
        next_event_time = self.next_event_time(abs_time)
        if next_event_time == 0:
            return None
        next_event_id = Event.event_id_from_class_and_time(self, next_event_time)
        return next_event_id

    dto: EventClassDto
    desc: EventDescription

    def get_sample_instance():
        return EventClass.new("btcusd", "BTCUSD", 6, 0, 1704067200, 86400, 1751367600)


# Holds a set of nonces for an event (one per digit); public and secret nonces
# Nonces to be used in the attestation signature
class Nonces:
    def __init__(self, nonces: list[Nonce]):
        self.n = nonces

    # Generate nonces. Note: this is a bit slow due to key operations
    def generate(event_id, range_digits):
        nonces = []
        for i in range(range_digits):
            # TODO use a non-deterministic, true random nonce here
            newnonce = dlcplazacryptlib.create_deterministic_nonce(event_id, i)
            nonce = Nonce(event_id=event_id, digit_index=i, nonce_pub=newnonce[1], nonce_sec=newnonce[0])
            nonces.append(nonce)
        print(".", end="")
        return Nonces(nonces)


class Outcome:
    def __init__(self, dto: OutcomeDto, digit_outcomes: list[DigitOutcome]):
        self.dto = dto
        self.digits = digit_outcomes

    # Create the outcome. May throw
    def create(outcome_value: str, event_id: str, event_desc: EventDescription, created_time: float, nonces: Nonces):
        outcome_dto = OutcomeDto(event_id=event_id, value=outcome_value, created_time=created_time)

        digit_values = event_desc.value_to_digits(float(outcome_value))
        # the number of digits, nonces, signatures
        n = event_desc.range_digits
        # check that digit_values[], nonces.n[] have enough elements
        if len(digit_values) < n:
            raise Exception(f"Not enough digit_values, {digit_values} {n}")
        if len(nonces.n) < n:
            raise Exception(f"Not enough nonces, {len(nonces.n)} {n}")

        digits = []
        for i in range(n):
            msg = Outcome.string_for_event(event_desc, event_id, i, digit_values[i])
            sig = dlcplazacryptlib.sign_schnorr_with_nonce(msg, nonces.n[i].nonce_sec, 0)
            digit_outcome = DigitOutcome(event_id, i, digit_values[i], nonces.n[i].nonce_pub, sig, msg)
            digits.append(digit_outcome)
        return Outcome(dto=outcome_dto, digit_outcomes=digits)

    def string_for_event(event_desc: EventDescription, event_id: str, digit_index: int, digit_outcome: int) -> str:
        s = event_desc.event_string_template_for_id(event_id)
        s = s.replace("{digit_index}", str(digit_index))
        s = s.replace("{digit_outcome}", str(digit_outcome))
        return s


class Event:
    """An individual event"""

    def __init__(self, dto: EventDto, event_class_dto: EventClassDto):
        self.dto = dto
        self.desc = EventClass(event_class_dto).desc
        self.event_class = event_class_dto.id
        # set later on-demand, on first use
        self._nonces = None  
        self.outcome = None

    def new(time, event_class: EventClass, signer_public_key: str):
        assert(event_class is not None)
        event_id = Event.event_id_from_class_and_time(event_class, time)
        string_template = event_class.desc.event_string_template_for_id(event_id)
        event_dto = EventDto(event_id=event_id, definition=event_class.dto.definition, time=time, string_template=string_template, signer_public_key=signer_public_key)
        return Event(event_dto, event_class.dto)

    # Construct event ID of the form 'btceur1748991600'
    def event_id_from_class_and_time(event_class, time):
        return event_class.dto.id + str(time)

    # Access nonces, Fill on-demand
    def get_nonces(self) -> Nonces:
        if not self._nonces:
            self._nonces = Nonces.generate(self.dto.event_id, self.desc.range_digits)
        return self._nonces

    def get_event_info(self):
        has_outcome = (self.outcome is not None)
        nonces = self.get_nonces()
        info = {
            "event_id": self.dto.event_id,
            "time_utc": self.dto.time,
            "time_utc_nice": str(datetime.fromtimestamp(self.dto.time, UTC)),
            "definition": self.desc.definition,
            "event_type": self.desc.event_type,
            "range_digits": self.desc.range_digits,
            "range_digit_low_pos": self.desc.range_digit_low_pos,
            "range_digit_high_pos": self.desc.get_digit_high_pos(),
            "range_unit": self.desc.get_unit(),
            "range_min_value": self.desc.get_minimum_value(),
            "range_max_value": self.desc.get_maximum_value(),
            "event_class": self.event_class,
            "signer_public_key": self.dto.signer_public_key,
            "string_template": self.dto.string_template,
            "has_outcome": has_outcome,
            # public nonces
            "nonces": list(map(lambda n: n.nonce_pub, nonces.n)),
        }
        if has_outcome:
            info["outcome_value"] = self.outcome.dto.value
            info["outcome_time"] = self.outcome.dto.created_time
            info["digits"] = list(map(lambda di: di.to_info(), self.outcome.digits))
        return info


# TODO:
# store in DB
# Store eventclasses, nonces, digitoutcomes, outcomes, publickeys separately
# No on-demand Nonce creation, no deterministic nonces. Filled at creation, later used from DB
class SimulatedDb:
    _event_classes: list[EventClassDto] = []
    # Holds all the events, past and future. Key is the ID
    _events: dict[str, Event] = {}

    def event_classes_clear(self):
        self._event_classes = []

    def event_classes_insert(self, ec: EventClassDto):
        self._event_classes.append(ec)

    def event_classes_len(self) -> int:
        return len(self._event_classes)

    def event_classes_get_all(self) -> list[EventClassDto]:
        return self._event_classes

    def event_classes_get_by_def(self, definition: str) -> EventClassDto:
        for ec in self._event_classes:
            if ec.definition == definition:
                return ec
        # Not found
        return None

    def events_clear(self):
        self._events = {}

    def events_append(self, more_events: list[Event]):
        self._events = {**self._events, **more_events}

    def events_len(self) -> int:
        return len(self._events)

    def events_get_by_id(self, event_id: str) -> Event | None:
        if event_id in self._events:
            return self._events[event_id]
        return None

    # Get the time of the earliest event without outcome
    def events_get_earliest_time_without_outcome(self) -> int:
        t = sys.maxsize - 10
        for _eid, e in self._events.items():
            if e.outcome is not None:
                continue
            if e.dto.time < t:
                t = e.dto.time
        return t

    def events_set_outcome(self, event_id, outcome):
        self._events[event_id].outcome = outcome

    # Get (the ID of) events in the past with no outcome
    def events_get_past_no_outcome(self, now) -> list[str]:
        # past events without outcome
        pe = []
        for _eid, e in self._events.items():
            if e.outcome is not None:
                continue
            if e.dto.time > now:
                continue
            pe.append(e.dto.event_id)
        return pe

    """Count the number of future events"""
    def events_count_future(self, current_time: int):
        c = 0
        for _eid, e in self._events.items():
            if e.dto.time > current_time:
                c += 1
        return c

    def events_get_filter(self, start_time: int, end_time: int, definition: str | None, limit: int) -> list[Event]:
        r = []
        for eid, e in self._events.items():
            if start_time != 0:
                if e.dto.time < start_time:
                    continue
            if end_time != 0:
                if e.dto.time > end_time:
                    continue
            if definition is not None:
                if e.desc.definition != definition:
                    continue
            r.append(e)
            if len(r) >= limit:
                break
        return r

    def events_get_ids_filter(self, start_time: int, end_time: int, definition: str | None, limit: int) -> list[str]:
        r = []
        for eid, e in self._events.items():
            if start_time != 0:
                if e.dto.time < start_time:
                    continue
            if end_time != 0:
                if e.dto.time > end_time:
                    continue
            if definition is not None:
                if e.desc.definition != definition:
                    continue
            r.append(eid)
            if len(r) >= limit:
                break
        return r

    def clear(self):
        self._event_classes = []
        self._events = {}


class Oracle:
    def __init__(self, public_key):
        self.db = SimulatedDb()
        self.public_key = public_key
        self.price_source = PriceSource()

    def clear(self):
        self.db.clear()

    def load_event_classes(self, event_classes):
        self.clear()
        for ec in event_classes:
            self.add_event_class(ec)

    def add_event_class(self, ec):
        print("Generating events.for event class '", ec.dto.id, "' ...")
        events = self.generate_events_from_class(ec=ec, signer_public_key=self.public_key)
        self.db.event_classes_insert(ec.dto)
        # Merge
        self.db.events_append(events)
        print(f"Loaded event class '{ec.dto.id}', generated {len(events)} events, total {self.db.events_len()}")

    def print(self):
        now = time.time()
        print(f"Oracle, with {self.db.events_count_future(now)} events ({self.db.events_len()} total), and {self.db.event_classes_len()} eventclasses")

    def generate_events_from_class(self, ec: EventClass, signer_public_key: str):
        e = {}
        t = ec.dto.repeat_first_time
        cnt = 0
        while t <= ec.dto.repeat_last_time:
            # create event
            ev = Event.new(event_class=ec, time=t, signer_public_key=signer_public_key)
            eid = ev.dto.event_id
            # print(cnt, " ", eid, ", ", ev.time, ' ', ev.desc.range_digits)
            e[eid] = ev
            t += ec.dto.repeat_period
            cnt += 1
        return e

    def get_oracle_info(self):
        return {
            "public_key": self.public_key
        }

    def get_oracle_status_time(self, current_time: float):
        future_count = self.db.events_count_future(current_time)
        return {
            "future_event_count": future_count,
            "total_event_count": self.db.events_len(),
            "current_time_utc": round(time.time(), 3),
        }

    def get_oracle_status(self):
        now = time.time()
        return self.get_oracle_status_time(now)

    def get_sample_instance(pubkey):
        o = Oracle(pubkey)
        # ev = EventClass.get_sample_instance()
        start_time = 1704067200 + 17 * 30 * 86400
        end_time = start_time + 18 * 30 * 86400
        o.load_event_classes(event_classes=[
            EventClass.new("btcusd", "BTCUSD", 7, 0, start_time, 10 * 60, end_time),
            EventClass.new("btceur", "BTCEUR", 7, 0, start_time, 12 * 3600, end_time),
        ])
        return o

    # Get event classes
    def get_event_classes(self):
        return list(map(lambda ec_dto: EventClass(ec_dto).to_info(), self.db.event_classes_get_all()))

    def get_event_class(self, definition: str) -> EventClass:
        if not definition:
            return None
        def_upper = definition.upper()
        dto = self.db.event_classes_get_by_def(def_upper)
        if dto == None:
            return None
        return EventClass(dto)

    def get_event_by_id(self, event_id: str):
        e = self.db.events_get_by_id(event_id)
        if not e:
            return {}
        return e.get_event_info()

    # Note: Max count is capped at the hard limit of 100 events, to prevent large responses
    def get_events_filter(self, start_time: int = 0, end_time = 0, definition: str = None, max_count: int = 100) -> list[dict]:
        if definition is not None:
            definition = definition.upper()
        max_count_hard_limit = 100
        max_count = min(max_count, max_count_hard_limit)
        events = self.db.events_get_filter(start_time, end_time, definition, max_count)
        event_infos = list(map(lambda e: e.get_event_info(), events))
        return event_infos

    # Note: a hard limit of 5000 limit is applied, to prevent very large responses
    def get_event_ids_filter(self, start_time: int = 0, end_time = 0, definition: str = None) -> list[str]:
        if definition is not None:
            definition = definition.upper()
        return self.db.events_get_ids_filter(start_time, end_time, definition, 5000)

    # Get the next instance of an event class, after the given time
    def get_next_event(self, definition: str = None, period: int = 60) -> dict:
        period_cap = max(period, 60)
        # Compute the next event, try to find that
        event_class = self.get_event_class(definition)
        if not event_class:
            return {}

        abs_time = math.floor(time.time()) + period_cap
        next_event_id = event_class.next_event_id(abs_time)
        # print("next_event_id", next_event_id)
        if not next_event_id:
            return {}

        event = self.db.events_get_by_id(next_event_id)
        if not event:
            return {}
        assert(event.time >= abs_time)
        return event.get_event_info()

    def get_price(self, symbol, time):
        return self.price_source.get_price_info(symbol, time).price

    def create_past_outcomes_time(self, current_time: float) -> int:
        cnt = 0
        # past events without outcome
        pe = self.db.events_get_past_no_outcome(current_time)
        print(f"Found {len(pe)} events in the past without outcome")
        for eid in pe:
            e = self.db.events_get_by_id(eid)
            symbol = e.desc.definition
            value = self.get_price(symbol, current_time)
            try:
                outcome = Outcome.create(str(value), e.dto.event_id, e.desc, current_time, e.get_nonces())
                self.db.events_set_outcome(e.dto.event_id, outcome)
            except Exception as ex:
                print(f"Exception while generating outcome, {ex}")
                # continue
            cnt += 1
        if cnt > 0:
            print(f"Generated outcomes for {cnt} past events")
        return cnt

    def create_past_outcomes(self) -> int:
        now = time.time()
        print("Checking for past outcome generation ...", round(now))
        return self.create_past_outcomes_time(now)

    def dummy_outcome_for_event(self, event_id):
        e = self.db.events_get_by_id(event_id)
        if e != None:
            # make a copy, we don't want to store the premature dummy outcome
            ecopy = copy.deepcopy(e)
            if e.outcome is None:
                # has no outcome yet
                symbol = e.desc.definition
                value = self.get_price(symbol, e.dto.time)
                now = time.time()
                try:
                    ecopy.outcome = Outcome.create(str(value), e.dto.event_id, e.desc, now, e.get_nonces())
                except Exception as ex:
                    print(f"Exception while generating outcome, {ex}")
                    return {}
            return ecopy.get_event_info()
        return {}

    def check_outcome_loop(self):
        print("check_outcome_loop started", round(time.time()))
        time.sleep(10)
        while True:
            self.create_past_outcomes()
            earliest = self.db.events_get_earliest_time_without_outcome()
            now = time.time()
            # wait a bit for the next event, but limit wait to min/max values
            towait_unbound = (earliest - now) / 2 - 1
            towait = min(max(towait_unbound, 0.01), 300)
            if towait > 0.5:
                print("Sleeping for", towait, "(", round(towait_unbound), ") ...")
            time.sleep(towait)

class OracleApp:
    oracle: Oracle

    def __init__(self):
        xpub = dlcplazacryptlib.init("./secret.sec", "password")
        public_key = dlcplazacryptlib.get_public_key(0)
        print("dlcplazacryptlib initialized, public key:", public_key)
        self.oracle = Oracle(public_key)
        random.seed()

    def get_singleton_instance() -> Oracle:
        global _singleton_app_instance
        if not _singleton_app_instance:
            _singleton_app_instance = OracleApp.create_sample_app_instance()
        return _singleton_app_instance

    def create_sample_app_instance() -> Oracle:
        app = OracleApp()
        public_key = dlcplazacryptlib.get_public_key(0)
        app.oracle = Oracle.get_sample_instance(public_key)
        global _outcome_loop_thread_started
        if not _outcome_loop_thread_started:
            _thread.start_new(outcome_loop_thread, (app.oracle, ))
        return app

    def get_oracle(self):
        self.oracle

    def get_current_price(self, symbol: str):
        now = time.time()
        value = self.oracle.price_source.get_price_info(symbol, now).price
        return value

    def get_current_prices(self):
        res = {}
        now = time.time()
        for symbol in self.oracle.price_source.get_symbols():
            value = self.oracle.price_source.get_price_info(symbol, now).price
            res[symbol] = value
        return res

    def get_current_price_info(self, symbol: str):
        now = time.time()
        info = self.oracle.price_source.get_price_info(symbol, now)
        return info

    def get_current_price_infos(self):
        res = {}
        now = time.time()
        for symbol in self.oracle.price_source.get_symbols():
            info = self.oracle.price_source.get_price_info(symbol, now)
            res[symbol] = info
        return res

def outcome_loop_thread(oracle):
    global _outcome_loop_thread_started
    _outcome_loop_thread_started = True
    oracle.check_outcome_loop()

