from oracle import EventDescription
import unittest


class EventDescriptionTestCase(unittest.TestCase):
    def test_template(self):
        assert EventDescription.event_string_template() == "Outcome:{event_id}:{digit_index}:{digit_outcome}", "Event otucome template, hardcoded"

    def test_template(self):
        event_id = "EID003"
        template = EventDescription.event_string_template_for_id(event_id)
        assert event_id in template, "EventID should be included in the template"
        assert template == "Outcome:EID003:{digit_index}:{digit_outcome}"


if __name__ == "__main__":
    unittest.main() # run all tests
