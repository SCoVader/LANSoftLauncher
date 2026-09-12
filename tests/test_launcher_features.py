import json

import pytest

from ui import build_system_action_payload, format_operating_time


def test_format_operating_time_uses_4_digit_hours_and_minutes():
    assert format_operating_time(3600 + 900) == "0001:15"
    assert format_operating_time(16 * 3600 + 42 * 60) == "0016:42"


def test_build_system_action_payload_serializes_action():
    payload = json.loads(build_system_action_payload("shutdown").decode("utf-8"))
    assert payload == {"action": "shutdown"}
