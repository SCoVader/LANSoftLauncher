import sys
from argparse import ArgumentParser

from PySide6.QtWidgets import QApplication

from ui import MainWindow


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    parser = ArgumentParser(prog="launcher")
    parser.add_argument("-c", "--config", dest="config", help="Path to config file (default: config.json)")
    args = parser.parse_args(argv)

    app = QApplication(sys.argv)
    window = MainWindow(config_path=args.config)
    window.show_on_monitor()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())