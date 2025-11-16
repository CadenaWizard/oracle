# Copyright (c) 2025-present Cadena Bitcoin
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.


class EventClassDto:
    """An event class, for periodically repeating similar events."""

    # - definition: The price source definition (a.k.a. symbol)
    # - event_string_template: Template for the string for a particular event.
    #   Example: "Outcome:{event_id}:{digit_index}:{digit_outcome}"
    # - repeat_first_time: The time of the first event (unix time), e.g. 1704067200
    # - repeat_period: The repetition period, in secs (e.g. 86400 for one day)
    # - repeat_offset: The offset compared to an entire multiple of repeat_period, recommended 0.
    # - repeat_last_time: The time of the firstlast event (unix time), e.g. 2019682800
    def __init__(self, id: str, create_time: int, definition: str, digits: int, digit_low_pos: int, event_string_template: str, repeat_first_time: int, repeat_period: int, repeat_offset: int, repeat_last_time: int, signer_public_key: str):
        self.id = id
        self.create_time = create_time
        self.definition = definition
        self.range_digits = digits
        self.range_digit_low_pos = digit_low_pos
        self.event_string_template = event_string_template
        self.repeat_first_time = repeat_first_time
        self.repeat_period = repeat_period
        self.repeat_offset = repeat_offset
        self.repeat_last_time = repeat_last_time
        self.signer_public_key = signer_public_key


# Outcome for one digit: index, value, nonce, sig
class DigitOutcome:
    # index: 0-based.left-to-right index of the digit
    # value: the outcome of the digit
    # msg_str: the exact string message for signing
    def __init__(self, event_id: str, index: int, value: int, nonce: str, signature: str, msg_str: str):
        self.event_id = event_id
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


# A pair of nonces, public and secret, for an outcome digit of an event
class Nonce:
    def __init__(self, event_id: str, digit_index: int, nonce_pub: str, nonce_sec: str):
        self.event_id = event_id
        self.digit_index = digit_index
        self.nonce_pub = nonce_pub
        self.nonce_sec = nonce_sec


class OutcomeDto:
    def __init__(self, event_id: str, value: str, created_time: float):
        self.event_id = event_id
        self.value = value
        self.created_time = created_time


class EventDto:
    def __init__(self, event_id: str, class_id: str, definition: str, time: int, string_template: str, signer_public_key: str):
        self.event_id = event_id
        self.class_id = class_id
        self.definition = definition
        self.time = time
        self.string_template = string_template
        self.signer_public_key = signer_public_key
