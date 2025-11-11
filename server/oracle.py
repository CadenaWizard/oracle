# Copyright (c) 2025-present Cadena Bitcoin
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

import dlcplazacryptlib
from dto import EventClassDto, EventDescriptionDto
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
        dto = EventDescriptionDto(
            definition=definition.upper(),
            digits=digits,
            digit_low_pos=digit_low_pos,
            event_string_template=EVENT_STRING_TEMPLATE_DEFAULT)
        self.dto = dto
        self.event_type = "numeric"

    def get_minimum_value(self) -> float:
        return 0

    # Compute smallest unit (1, 10, 100, ...) from digit_low_pos (0, 1, 2, ...)
    def get_unit(self) -> int:
        return power_of_ten(self.dto.range_digit_low_pos)

    # Compute high digit pos, from low digit pos and digits
    # E.g. low=0, digits=6 => high=5
    def get_digit_high_pos(self) -> int:
        return self.dto.range_digit_low_pos + self.dto.range_digits - 1

    def get_maximum_value(self) -> float:
        max_val_units = power_of_ten(self.dto.range_digits) - 1
        return max_val_units * self.get_unit()

    # Template for the string for a particular event.
    # Example: "Outcome:{event_id}:{digit_index}:{digit_outcome}"
    def event_string_template(self) -> str:
        return self.dto.event_string_template

    def event_string_template_for_id(self, event_id: str) -> str:
        template = self.dto.event_string_template
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
        n = self.dto.range_digits
        while len(normalized_str) < n:
            normalized_str = '0' + normalized_str
        res = []
        for i in range(n):
            res.append(int(normalized_str[i]))
        return res

    # Convert from digits to actual value, e.g. e.g. [0,8,5,6,5] -> 85650 (5 digits, unit 10.0)
    def digits_to_value(self, digits: list[int]) -> float:
        v = 0
        n = self.dto.range_digits
        for i in range(n):
            v = 10 * v + digits[i]
        value = v * self.get_unit() + self.get_minimum_value()
        return value

    def to_info(self):
        return {
            "definition": self.dto.definition,
            "event_type": self.event_type,
            "range_digits": self.dto.range_digits,
            "range_digit_low_pos": self.dto.range_digit_low_pos,
            "range_digit_high_pos": self.get_digit_high_pos(),
            "range_unit": self.get_unit(),
            "range_min_value": self.get_minimum_value(),
            "range_max_value": self.get_maximum_value(),
        }

    dto: EventDescriptionDto
    # Event type: supported values: 'numeric'
    event_type: str = "numeric"


class EventClass:
    """An event class, typically for periodically repeating similar events."""

    def __init__(self, id, definition, digits, digit_low_pos, repeat_first_time, repeat_period, repeat_last_time):
        definition_obj = EventDescription(definition=definition, digits=digits, digit_low_pos=digit_low_pos)
        dto = EventClassDto(id=id, definition=definition, repeat_first_time=repeat_first_time, repeat_period=repeat_period, repeat_last_time=repeat_last_time)
        self.dto = dto
        self.desc = definition_obj

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
        return EventClass("btcusd", "BTCUSD", 6, 0, 1704067200, 86400, 1751367600)

# Outcome for one digit: index, value, nonce, sig
class DigitOutcome:
    # 0-based.left-to-right index of the digit
    index: int
    # the outcome of the digit
    value: int
    nonce: str
    signature: str
    # the exact string message for signing
    msg_str: str

    def __init__(self, index, value, nonce, signature, msg_str):
        self.index = index
        self.value = value
        self.nonce = nonce
        self.signature = signature
        self.msg_str = msg_str

    def to_info(self):
        return {
            "index": self.index,
            "value": self.value,
            "nonce": self.nonce,
            "signature": self.signature,
            "msg_str": self.msg_str,
        }


# Holds a set of nonces for an event (one per digit); public and secret nonces
class Nonces:
    # Generate nonces. Note: this is a bit slow due to key operations
    def __init__(self, event_id, range_digits):
        self.nonces_pub = []
        self.nonces_sec = []
        for i in range(range_digits):
            # TODO use a non-deterministic, true random nonce here
            newnonce = dlcplazacryptlib.create_deterministic_nonce(event_id, i)
            self.nonces_sec.append(newnonce[0])
            self.nonces_pub.append(newnonce[1])
        print(".", end="")

    # A nonce for each digit
    # Nonces to be used in the attestation signature
    # Public key, hex string
    nonces_pub: list[str] = []
    # The secret part of the nonces
    nonces_sec: list[str] = []


class Outcome:
    # Create the outcome. May throw
    def __init__(self, outcome_value: str, event_id: str, event_desc: EventDescription, created_time: float, nonces: Nonces):
        digit_values = event_desc.value_to_digits(outcome_value)
        self.value = event_desc.digits_to_value(digit_values)
        self.created_time = created_time

        # the number of digits, nonces, signatures
        n = event_desc.range_digits
        # check that digit_values[], nonces_sec[], nonces_pub[] have enough elements
        if len(digit_values) < n:
            raise Exception(f"Not enough digit_values, {digit_values} {n}")
        if (len(nonces.nonces_pub) < n) | (len(nonces.nonces_sec) < n):
            raise Exception(f"Not enough nonces, {len(nonces.nonces_pub)} {len(nonces.nonces_sec)} {n}")

        self.digits = []
        for i in range(n):
            msg = Outcome.string_for_event(event_id, i, digit_values[i])
            sig = dlcplazacryptlib.sign_schnorr_with_nonce(msg, nonces.nonces_sec[i], 0)
            digit_outcome = DigitOutcome(i, digit_values[i], nonces.nonces_pub[i], sig, msg)
            self.digits.append(digit_outcome)

    def string_for_event(event_id: str, digit_index: int, digit_outcome: int) -> str:
        s = EventDescription.event_string_template_for_id(event_id)
        s = s.replace("{digit_index}", str(digit_index))
        s = s.replace("{digit_outcome}", str(digit_outcome))
        return s

    value: float = ""
    digits: list[DigitOutcome] = []
    # Time when the outcome was processed, unix time
    created_time: float = 0


class Event:
    """An individual event"""

    def __init__(self, time, event_class=None, id=None, definition=None, digits=None, unit=None, signer_public_key: str = ""):
        if event_class is not None:
            # constructor with a class
            self.event_id = Event.event_id_from_class_and_time(event_class, time)
            self.desc = event_class.desc
            self.event_class = event_class.dto.id
        else:
            self.event_id = id
            self.desc = EventDescription(definition, digits, unit)
            self.event_class = ""
        self.time = time
        self.signer_public_key = signer_public_key
        # set later on-demand, on first use
        self._nonces = None  
        self.string_template = EventDescription.event_string_template_for_id(self.event_id)

    # Construct event ID of the form 'btceur1748991600'
    def event_id_from_class_and_time(event_class, time):
        return event_class.dto.id + str(time)

    # Access nonces, Fill on-demand
    def get_nonces(self) -> Nonces:
        if not self._nonces:
            self._nonces = Nonces(self.event_id, self.desc.range_digits)
        return self._nonces

    def get_event_info(self):
        has_outcome = (self.outcome is not None)
        nonces = self.get_nonces()
        info = {
            "event_id": self.event_id,
            "time_utc": self.time,
            "time_utc_nice": str(datetime.fromtimestamp(self.time, UTC)),
            "definition": self.desc.definition,
            "event_type": self.desc.event_type,
            "range_digits": self.desc.range_digits,
            "range_digit_low_pos": self.desc.range_digit_low_pos,
            "range_digit_high_pos": self.desc.get_digit_high_pos(),
            "range_unit": self.desc.get_unit(),
            "range_min_value": self.desc.get_minimum_value(),
            "range_max_value": self.desc.get_maximum_value(),
            "event_class": self.event_class,
            "signer_public_key": self.signer_public_key,
            "string_template": self.string_template,
            "has_outcome": has_outcome,
            "nonces": nonces.nonces_pub,
        }
        if has_outcome:
            info["outcome_value"] = self.outcome.value
            info["outcome_time"] = self.outcome.created_time
            info["digits"] = list(map(lambda di: di.to_info(), self.outcome.digits))
        return info

    event_id: str = ""
    # The time of the event (unix time)
    time: int = 1767222000
    desc: EventDescription
    # If it's the member of an event class
    event_class: str = ""
    # The signer (oracle) public key, to be used or used for signing
    signer_public_key: str = ""
    # A nonce for each digit, access it through get_nonces()
    _nonces: Nonces = None
    # The message string template for this event
    string_template: str = ""
    outcome: Outcome = None

class Oracle:
    public_key: str = ""
    event_classes = []
    # Holds all the events, past and future. Key is the ID
    events = {}
    price_source = PriceSource()

    def __init__(self, public_key):
        self.clear()
        self.public_key = public_key

    def clear(self):
        self.event_classes = []
        self.events = {}

    def load_event_classes(self, event_classes):
        self.clear()
        for ec in event_classes:
            self.add_event_class(ec)

    def add_event_class(self, ec):
        print("Generating events.for event class '", ec.dto.id, "' ...")
        events = self.generate_events_from_class(ec=ec, signer_public_key=self.public_key)
        self.event_classes.append(ec)
        # Merge
        self.events = {**self.events, **events}
        print(f"Loaded event class '{ec.dto.id}', generated {len(events)} events, total {len(self.events)}")

    def print(self):
        now = time.time()
        print("Oracle, with",
            self.count_future_events(now),
            "events (",
            len(self.events), 
            "total), and", len(self.event_classes), "eventclasses")

    def generate_events_from_class(self, ec: EventClass, signer_public_key: str):
        e = {}
        t = ec.dto.repeat_first_time
        cnt = 0
        while t <= ec.dto.repeat_last_time:
            # create event
            ev = Event(event_class=ec, time=t, signer_public_key=signer_public_key)
            eid = ev.event_id
            # print(cnt, " ", eid, ", ", ev.time, ' ', ev.desc.range_digits)
            e[eid] = ev
            t += ec.dto.repeat_period
            cnt += 1
        return e

    def get_oracle_info(self):
        return {
            "public_key": self.public_key
        }

    def get_oracle_status(self):
        now = time.time()
        future_count = self.count_future_events(now)
        return {
            "future_event_count": future_count,
            "total_event_count": len(self.events),
            "current_time_utc": round(time.time(), 3),
        }

    def get_sample_instance(pubkey):
        o = Oracle(pubkey)
        # ev = EventClass.get_sample_instance()
        start_time = 1704067200 + 17 * 30 * 86400
        end_time = start_time + 18 * 30 * 86400
        o.load_event_classes(event_classes=[
            EventClass("btcusd", "BTCUSD", 7, 0, start_time, 10 * 60, end_time),
            EventClass("btceur", "BTCEUR", 7, 0, start_time, 12 * 3600, end_time),
        ])
        return o

    # Get event classes
    def get_event_classes(self):
        return list(map(lambda ec: ec.to_info(), self.event_classes))

    def get_event_class(self, definition: str) -> EventClass:
        if not definition:
            return None
        def_upper = definition.upper()
        for ec in self.event_classes:
            if ec.desc.definition == def_upper:
                return ec
        # Not found
        return None

    def get_event_by_id_intern(self, event_id: str):
        if event_id in self.events:
            return self.events[event_id]
        return None

    def get_event_by_id(self, event_id: str):
        e = self.get_event_by_id_intern(event_id)
        if not e:
            return {}
        return e.get_event_info()

    # Note: Max count is capped at the hard limit of 100 events, to prevent laerge responses
    def get_events_filter(self, start_time: int = 0, end_time = 0, definition: str = None, max_count: int = 100):
        if definition is not None:
            definition = definition.upper()
        r = []
        max_count_hard_limit = 100
        max_count = min(max_count, max_count_hard_limit)
        for _eid, e in self.events.items():
            if start_time != 0:
                if e.time < start_time:
                    continue
            if end_time != 0:
                if e.time > end_time:
                    continue
            if definition is not None:
                if e.desc.definition != definition:
                    continue
            r.append(e.get_event_info())
            if len(r) >= max_count:
                break
        return r

    # Note: a hard limit of 5000 limit is applied, to prevent very large responses
    def get_event_ids_filter(self, start_time: int = 0, end_time = 0, definition: str = None):
        if definition is not None:
            definition = definition.upper()
        r = []
        max_count_hard_limit = 5000
        for eid, e in self.events.items():
            if start_time != 0:
                if e.time < start_time:
                    continue
            if end_time != 0:
                if e.time > end_time:
                    continue
            if definition is not None:
                if e.desc.definition != definition:
                    continue
            r.append(eid)
            if len(r) >= max_count_hard_limit:
                break
        return r

    # Get the next instance of an event class, after the given time
    def get_next_event(self, definition: str = None, period: int = 60):
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

        event = self.get_event_by_id_intern(next_event_id)
        if not event:
            return {}
        assert(event.time >= abs_time)
        return event.get_event_info()

    """Count the number of future events"""
    def count_future_events(self, current_time: int):
        c = 0
        for _eid, e in self.events.items():
            if e.time > current_time:
                c += 1
        return c

    def get_price(self, symbol, time):
        return self.price_source.get_price_info(symbol, time).price

    def create_past_outcomes(self):
        now = time.time()
        print("Checking for past outcome generation ...", round(now))
        cnt = 0
        for eid, e in self.events.items():
            if e.outcome is not None:
                continue
            if e.time > now:
                continue
            # has no outcome yet and is in the past
            symbol = e.desc.definition
            value = self.get_price(symbol, now)
            try:
                outcome = Outcome(str(value), e.event_id, e.desc, now, e.get_nonces())
                self.events[eid].outcome = outcome
            except Exception as ex:
                print(f"Exception while generating outcome, {ex}")
                # continue
            cnt += 1
        if cnt > 0:
            print("Generated outcomes for", cnt, "past events")

    # Get the time of the earliest event without outcome
    def get_earliest_event_time_without_outcome(self) -> int:
        t = sys.maxsize - 10
        for _eid, e in self.events.items():
            if e.outcome is not None:
                continue
            if e.time < t:
                t = e.time
        return t

    def dummy_outcome_for_event(self, event_id):
        if event_id in self.events:
            e = self.events[event_id]
            # make a copy, we don't want to store the premature dummy outcome
            ecopy = copy.deepcopy(e)
            if e.outcome is None:
                # has no outcome yet
                symbol = e.desc.definition
                value = self.get_price(symbol, e.time)
                now = time.time()
                try:
                    ecopy.outcome = Outcome(str(value), e.event_id, e.desc, now, e.get_nonces())
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
            earliest = self.get_earliest_event_time_without_outcome()
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

