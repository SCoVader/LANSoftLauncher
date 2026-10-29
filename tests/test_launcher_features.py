import json
from unittest.mock import Mock, patch

from app_logging import configure_logging
from ui import (
    MainWindow,
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


def test_debug_system_actions_are_logged_without_execution(tmp_path):
    log_path = tmp_path / "launcher.log"
    logger = configure_logging(log_path)
    file_handler = logger.handlers[-1]
    try:
        for action in ("shutdown", "reboot"):
            window = Mock()
            window.debug = True
            with patch("ui.subprocess.run") as system_action:
                MainWindow._execute_system_action(window, action)

            window._persist_operating_time.assert_called_once_with()
            system_action.assert_not_called()
            assert (
                f"System action recorded (debug mode, not executed): {action}"
                in log_path.read_text(encoding="utf-8")
            )
    finally:
        logger.removeHandler(file_handler)
        file_handler.close()


def test_normal_system_actions_execute_original_commands():
    window = Mock()
    window.debug = False

    for action, command in (
        ("shutdown", ["shutdown", "/s", "/t", "0"]),
        ("reboot", ["shutdown", "/r", "/t", "0"]),
    ):
        with patch("ui.subprocess.run", return_value=Mock(returncode=0)) as run:
            MainWindow._execute_system_action(window, action)

        run.assert_called_once_with(command, check=False)
    assert window._persist_operating_time.call_count == 2


def test_debug_system_action_request_is_not_broadcast():
    window = Mock()
    window.debug = True

    MainWindow._request_system_action(window, "shutdown")

    window._execute_system_action.assert_called_once_with("shutdown")
    window._broadcast_system_action.assert_not_called()


def test_normal_system_action_request_broadcasts_and_executes():
    window = Mock()
    window.debug = False

    MainWindow._request_system_action(window, "shutdown")

    window._broadcast_system_action.assert_called_once_with("shutdown")
    window._execute_system_action.assert_called_once_with("shutdown")


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
