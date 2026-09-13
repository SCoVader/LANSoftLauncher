import sys
from argparse import ArgumentParser
from pathlib import Path

from PySide6.QtWidgets import QApplication

from ui import MainWindow, OPERATING_TIME_FILE_NAME, PASSWORD_FILE_NAME, save_operating_time, verify_admin_password
from paths import resource_path

def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    parser = ArgumentParser(prog="launcher")
    parser.add_argument("-c", "--config", dest="config", help="Path to config file (default: config.json)")
    parser.add_argument("--reset-clock", metavar="PASSWORD", help="Reset accumulated operating time")
    args = parser.parse_args(argv)

    config_path = Path(args.config) if args.config else Path(resource_path("config.json"))
    if args.reset_clock is not None:
        password_path = config_path.parent / PASSWORD_FILE_NAME
        if not verify_admin_password(password_path, args.reset_clock):
            print("Invalid administrator password.")
            return 1
        save_operating_time(config_path.parent / OPERATING_TIME_FILE_NAME, 0)
        print("Operating time reset.")
        return 0

    app = QApplication(["launcher", *(argv or [])])
    window = MainWindow(config_path=str(config_path))
    window.show_on_monitor()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())