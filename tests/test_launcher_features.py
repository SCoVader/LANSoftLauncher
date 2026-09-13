import json

import pytest

from ui import (
    build_system_action_payload,
    format_operating_time,
    load_operating_time,
    save_admin_password,
    save_operating_time,
    verify_admin_password,
)


def test_format_operating_time_uses_4_digit_hours_and_minutes():
    assert format_operating_time(3600 + 900) == "0001:15"
    assert format_operating_time(16 * 3600 + 42 * 60) == "0016:42"


def test_build_system_action_payload_serializes_action():
    payload = json.loads(build_system_action_payload("shutdown").decode("utf-8"))
    assert payload == {"action": "shutdown"}


def test_binary_admin_password_and_operating_time_records(tmp_path):
    password_path = tmp_path / "admin_password.bin"
    operating_time_path = tmp_path / "operating_time.bin"

    save_admin_password(password_path, "secret")
    save_operating_time(operating_time_path, 3723)

    assert verify_admin_password(password_path, "secret")
    assert not verify_admin_password(password_path, "wrong")
    assert load_operating_time(operating_time_path) == 3723
    assert b"secret" not in password_path.read_bytes()
    assert operating_time_path.read_bytes() != b"3723"
