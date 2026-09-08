import sys

from PySide6.QtWidgets import QApplication

from ui import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show_on_monitor()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())