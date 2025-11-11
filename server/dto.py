# Copyright (c) 2025-present Cadena Bitcoin
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.


class EventDescriptionDto:
    """Common attributes of an event"""

    def __init__(self, definition: str, digits: int, digit_low_pos: int, event_string_template: str):
        self.definition = definition
        self.range_digits = digits
        self.range_digit_low_pos = digit_low_pos
        # Template for the string for a particular event.
        # Example: "Outcome:{event_id}:{digit_index}:{digit_outcome}"
        self.event_string_template = event_string_template


class EventClassDto:
    """An event class, typically for periodically repeating similar events."""

    # - repeat_first_time: The time of the first event (unix time), e.g. 1704067200
    # - repeat_period: The repetition period, in secs (e.g. 86400 for one day)
    # - repeat_last_time: The time of the firstlast event (unix time), e.g. 2019682800
    def __init__(self, id: str, definition: str, repeat_first_time: int, repeat_period: int, repeat_last_time: int):
        self.id = id
        self.definition = definition
        self.repeat_first_time = repeat_first_time
        self.repeat_period = repeat_period
        self.repeat_last_time = repeat_last_time

