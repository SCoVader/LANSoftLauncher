import sys
import json
import subprocess
from pathlib import Path
from PySide6.QtWidgets import QApplication, QMainWindow, QLabel, QPushButton, QVBoxLayout, QWidget
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QGuiApplication, QCursor

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kiosk Launcher")

        # Load apps configuration (apps.json) or use defaults
        self.config_path = Path(__file__).parent / "apps.json"
        self.apps = self.load_apps()

        # Black background, centered buttons
        self.setStyleSheet("background-color: black;")

        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.label = QLabel("", alignment=Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("color: white; font-size: 18px;")
        layout.addWidget(self.label)

        # Create a button for each configured app
        for entry in self.apps:
            text = entry.get("name", "Launch")
            cmd = entry.get("cmd", "")
            btn = QPushButton(text)
            btn.setFixedSize(420, 140)
            btn.setStyleSheet("font-size:24px; background-color:#222; color: white; border-radius:8px;")
            btn.clicked.connect(self.make_launcher(cmd))
            layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)

        # Allow Esc to quit
        self.shortcut_quit = QApplication.instance()

        container = QWidget()
        container.setLayout(layout)
        container.setContentsMargins(0, 0, 0, 0)
        self.setCentralWidget(container)

    def load_apps(self):
        default = [
            {"name": "Notepad", "cmd": "notepad.exe"},
            {"name": "Calculator", "cmd": "calc.exe"},
            {"name": "Paint", "cmd": "mspaint.exe"}
        ]
        try:
            if self.config_path.exists():
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list) and data:
                        return data
        except Exception:
            pass
        # If no config present, write a default one for the user to edit
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(default, f, indent=2)
        except Exception:
            pass
        return default

    def make_launcher(self, cmd):
        def _launch():
            try:
                # Use shell=True to allow commands or executable names
                subprocess.Popen(cmd, shell=True)
            except Exception:
                try:
                    subprocess.Popen([cmd])
                except Exception:
                    pass
            # Give the launched app a moment to start, then exit launcher
            QTimer.singleShot(150, QApplication.quit)
        return _launch

    def on_button_click(self):
        self.label.setText("Button Clicked!")

if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = MainWindow()

    # Try to show on the screen where the mouse currently is (works for multi-monitor setups)
    try:
        screen = QGuiApplication.screenAt(QCursor.pos())
        if screen is None:
            screen = QGuiApplication.primaryScreen()
        if screen:
            geom = screen.geometry()
            window.setGeometry(geom)
    except Exception:
        pass

    window.showFullScreen()
    sys.exit(app.exec())