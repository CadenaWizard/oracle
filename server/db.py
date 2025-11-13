# Copyright (c) 2025-present Cadena Bitcoin
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

from dto import DigitOutcome, EventClassDto, EventDto, Nonce, OutcomeDto

import sys


# TODO store in DB
# TODO Store publickeys separately
# TODO No on-demand Nonce creation, no deterministic nonces. Filled at creation, later used from DB
class EventStorage:
    _event_classes: list[EventClassDto] = []
    # Holds  nonces, key is event ID
    _nonces: dict[str, list[Nonce]] = {}
    # Holds all the events, past and future. Key is the ID
    _events: dict[str, EventDto] = {}
    # Holds digit outcomes, key is event ID
    _digitoutcomes: dict[str, list[DigitOutcome]] = {}
    # Holds outcomes, key is event ID
    _outcomes: dict[str, OutcomeDto] = {}

    def clear(self):
        self._event_classes = []
        self._nonces = {}
        self._events = {}
        self._digitoutcomes = {}
        self._outcomes = {}

    def print_stats(self):
        print(f"DB stats: evcl: {len(self._event_classes)}  nonce: {len(self._nonces)}  ev: {len(self._events)}  diou: {len(self._digitoutcomes)}  outcome: {len(self._outcomes)}")

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

    def nonces_insert_one(self, nonce: Nonce):
        eid = nonce.event_id
        if eid not in self._nonces:
            self._nonces[eid] = []
        self._nonces[eid].append(nonce)

    def nonces_insert(self, nonces: list[Nonce]):
        for n in nonces:
            self.nonces_insert_one(n)

    def nonces_get(self, event_id: str) -> list[Nonce]:
        if event_id not in self._nonces:
            return []
        return self._nonces[event_id]

    def events_append(self, more_events: dict[str, EventDto]):
        self._events = {**self._events, **more_events}

    def events_len(self) -> int:
        return len(self._events)

    def events_get_by_id(self, event_id: str) -> EventDto | None:
        if event_id not in self._events:
            return None
        return self._events[event_id]

    # Get the time of the earliest event without outcome
    def events_get_earliest_time_without_outcome(self) -> int:
        t = sys.maxsize - 10
        for eid, e in self._events.items():
            if self.outcomes_exists(eid):
                continue
            if e.time < t:
                t = e.time
        return t

    # Get (the ID of) events in the past with no outcome
    def events_get_past_no_outcome(self, now) -> list[str]:
        # past events without outcome
        pe = []
        for eid, e in self._events.items():
            if self.outcomes_exists(eid):
                continue
            if e.time > now:
                continue
            pe.append(e.event_id)
        return pe

    """Count the number of future events"""
    def events_count_future(self, current_time: int):
        c = 0
        for _eid, e in self._events.items():
            if e.time > current_time:
                c += 1
        return c

    def events_get_ids_filter(self, start_time: int, end_time: int, definition: str | None, limit: int) -> list[str]:
        r = []
        for eid, e in self._events.items   ():
            if start_time != 0:
                if e.time < start_time:
                    continue
            if end_time != 0:
                if e.time > end_time:
                    continue
            if definition is not None:
                if e.definition != definition:
                    continue
            r.append(eid)
            if len(r) >= limit:
                break
        return r

    def digitoutcomes_insert(self, event_id: str, digit_outcome_list: list[DigitOutcome]):
        self._digitoutcomes[event_id] = digit_outcome_list

    def digitoutcomes_get(self, event_id: str) -> list[DigitOutcome]:
        if event_id not in self._digitoutcomes:
            return []
        return self._digitoutcomes[event_id]

    def outcomes_get(self, event_id: str) -> OutcomeDto | None:
        if event_id in self._outcomes:
            return self._outcomes[event_id]
        return None

    def outcomes_exists(self, event_id: str) -> bool:
        if event_id in self._outcomes:
            return True
        return False

    def outcomes_insert(self, o: OutcomeDto):
        self._outcomes[o.event_id] = o
