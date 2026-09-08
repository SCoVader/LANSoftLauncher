import json
import subprocess
from pathlib import Path

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication, QLabel, QMainWindow, QPushButton, QVBoxLayout, QWidget

from config import load_config
from network import TCPClient, TCPServer


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kiosk Launcher")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)

        self.config_path = Path(__file__).resolve().parent / "apps.json"
        self.config = load_config(self.config_path)
        self.apps = self.config.get("apps", [])
        self.role = self.config.get("role", "standalone")
        self.server_host = self.config.get("server_host", "")
        self.port = int(self.config.get("port", 8765))

        self.setStyleSheet("background-color: black;")

        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.label = QLabel("", alignment=Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("color: white; font-size: 18px;")
        layout.addWidget(self.label)

        if self.role == "listener":
            self.label.setText("Waiting for instructions...")
            self.client = TCPClient(self.server_host, self.port, self.handle_remote_launch)
            self.client.start()
        else:
            for entry in self.apps:
                text = entry.get("name", "Launch")
                cmd = entry.get("cmd", "")
                btn = QPushButton(text)
                btn.setFixedSize(420, 140)
                btn.setStyleSheet("font-size:24px; background-color:#222; color: white; border-radius:8px;")
                btn.clicked.connect(self.make_instructor_launcher(cmd))
                layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)

            if self.role == "instructor":
                self.server = TCPServer(self.port)
                self.server.start()

        container = QWidget()
        container.setLayout(layout)
        container.setContentsMargins(0, 0, 0, 0)
        self.setCentralWidget(container)

    def _start_app(self, cmd: str):
        try:
            subprocess.Popen(cmd, shell=True)
        except Exception:
            try:
                subprocess.Popen([cmd])
            except Exception:
                pass

    def _exit_launcher(self):
        QTimer.singleShot(150, QApplication.quit)

    def make_instructor_launcher(self, cmd: str):
        def _launch_and_broadcast():
            self._start_app(cmd)
            try:
                if hasattr(self, "server"):
                    payload = (json.dumps({"cmd": cmd}) + "\n").encode("utf-8")
                    self.server.broadcast(payload)
            except Exception:
                pass
            self._exit_launcher()

        return _launch_and_broadcast

    def handle_remote_launch(self, cmd: str):
        self._start_app(cmd)
        self._exit_launcher()

    def show_on_monitor(self):
        geom = QGuiApplication.primaryScreen().geometry()
        screens = QGuiApplication.screens()
        if screens:
            for screen in screens:
                geom = geom.united(screen.geometry())
        self.setGeometry(geom)
        self.show()

