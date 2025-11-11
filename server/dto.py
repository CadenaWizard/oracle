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


