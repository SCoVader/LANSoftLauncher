import logging
import subprocess
import sys
from argparse import ArgumentParser
from pathlib import Path
from typing import Callable

from PySide6.QtWidgets import QApplication

from ui import MainWindow, OPERATING_TIME_FILE_NAME, PASSWORD_FILE_NAME, save_operating_time, verify_admin_password
from paths import resource_path
from app_logging import configure_logging
from config import load_config
from system_actions import execute_system_action


LOG_FILE_NAME = "launcher.log"
logger = logging.getLogger("lansoftlauncher")


def execute_config_command(config: dict, selection: int) -> int:
    apps = config.get("apps", [])
    if not isinstance(apps, list):
        print("Configuration actions must be a list.")
        return 2
    if selection <= 0 or selection > len(apps):
        print(f"Invalid command number: {selection}")
        return 2

    entry = apps[selection - 1]
    if not isinstance(entry, dict):
        print(f"Configuration action {selection} is invalid.")
        return 2
    command = entry.get("cmd")
    if not isinstance(command, str) or not command.strip():
        print(f"Configuration action {selection} has no command.")
        return 2

    try:
        subprocess.Popen(command, shell=True)
    except (OSError, ValueError):
        logger.exception("Failed to launch configured command: %s", command)
        print(f"Failed to launch command: {command}")
        return 1

    logger.info("Configured command launched: %s", command)
    return 0


def run_system_action_menu(
    debug: bool,
    input_fn: Callable[[str], str],
    output_fn: Callable[[str], None],
) -> bool:
    actions = {
        "1": ("Shutdown", "shutdown"),
        "2": ("Reboot", "reboot"),
        "3": ("Toggle mute", "mute_toggle"),
    }
    output_fn("System actions:")
    for number, (name, _) in actions.items():
        output_fn(f"{number}. {name}")
    output_fn("0. Back")
    try:
        selection = input_fn("Select a system action: ").strip()
    except EOFError:
        return False
    if selection == "0":
        return True
    action = actions.get(selection)
    if action is None:
        output_fn("Invalid system action.")
        return True
    _, action_name = action
    succeeded = execute_system_action(action_name, debug=debug)
    if action_name in {"shutdown", "reboot"} and succeeded and not debug:
        return False
    return True


def run_terminal_menu(
    config: dict,
    debug: bool,
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
) -> int:
    apps = config.get("apps", [])
    if not isinstance(apps, list):
        output_fn("Configuration actions must be a list.")
        return 2

    while True:
        output_fn("0. System actions")
        for index, entry in enumerate(apps, start=1):
            name = entry.get("name", f"Action {index - 1}") if isinstance(entry, dict) else f"Action {index - 1}"
            output_fn(f"{index}. {name}")
        output_fn("q. Quit")

        try:
            selection = input_fn("Select an option: ").strip().lower()
        except EOFError:
            return 0
        if selection in {"q", "quit", "exit"}:
            return 0
        if selection == "0":
            should_continue = run_system_action_menu(debug, input_fn, output_fn)
            if not should_continue:
                return 0
            continue

        try:
            command_number = int(selection)
        except ValueError:
            output_fn("Invalid selection.")
            continue
        result = execute_config_command(config, command_number)
        if result == 2:
            continue


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    parser = ArgumentParser(prog="launcher")
    parser.add_argument("-c", "--config", dest="config", help="Path to config file (default: config.json)")
    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="Log system actions without executing or broadcasting them",
    )
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "-t",
        "--terminal",
        action="store_true",
        help="Run an interactive terminal menu without opening the UI",
    )
    mode_group.add_argument(
        "-e",
        "--execute",
        type=int,
        metavar="N",
        help="Execute numbered config command N (1 is the first config action)",
    )
    parser.add_argument("--reset-clock", metavar="PASSWORD", help="Reset accumulated operating time")
    args = parser.parse_args(argv)

    config_path = Path(args.config) if args.config else Path(resource_path("config.json"))
    logger = configure_logging(config_path.parent / LOG_FILE_NAME)
    logger.info("Launcher starting with config: %s", config_path)
    logger.info("Debug mode enabled: %s", args.debug)
    if args.reset_clock is not None:
        password_path = config_path.parent / PASSWORD_FILE_NAME
        if not verify_admin_password(password_path, args.reset_clock):
            logger.warning("Operating-time reset rejected: invalid administrator password")
            print("Invalid administrator password.")
            return 1
        save_operating_time(config_path.parent / OPERATING_TIME_FILE_NAME, 0)
        logger.info("Operating time reset")
        print("Operating time reset.")
        return 0

    if args.execute is not None:
        config = load_config(config_path)
        logger.info("Executing configured command selection: %s", args.execute)
        return execute_config_command(config, args.execute)
    if args.terminal:
        config = load_config(config_path)
        logger.info("Starting terminal menu")
        return run_terminal_menu(config, args.debug)

    app = QApplication(["launcher"])
    window = MainWindow(config_path=str(config_path), debug=args.debug)
    window.show_on_monitor()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())