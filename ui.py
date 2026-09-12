import ctypes
import json
import os
import subprocess
import time
from pathlib import Path

from PySide6.QtCore import QTimer, Qt, QSize
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtWidgets import QApplication, QLabel, QHBoxLayout, QMainWindow, QPushButton, QVBoxLayout, QWidget

from config import load_config
from network import TCPClient, TCPServer


def format_operating_time(total_seconds: float | int) -> str:
    total = max(0, int(total_seconds))
    hours, remainder = divmod(total, 3600)
    minutes = remainder // 60
    return f"{hours:04d}:{minutes:02d}"


def build_system_action_payload(action: str) -> bytes:
    return (json.dumps({"action": action}) + "\n").encode("utf-8")


class MainWindow(QMainWindow):
    def __init__(self, config_path: str | None = None):
        super().__init__()
        self.setWindowTitle("Kiosk Launcher")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        if config_path:
            self.config_path = Path(config_path)
        else:
            self.config_path = Path(__file__).resolve().parent / "config.json"
        self.config = load_config(self.config_path)
        self.apps = self.config.get("apps", [])
        self.role = self.config.get("role", "standalone")
        self.server_host = self.config.get("server_host", "")
        self.port = int(self.config.get("port", 8765))
        self._sound_muted = False
        self._started_at = time.monotonic()

        self.setStyleSheet("background-color: black;")

        self.layout = QVBoxLayout()
        self.layout.setSpacing(20)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.label = QLabel("", alignment=Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("color: white; font-size: 18px;")
        self.layout.addWidget(self.label)

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
                self.layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)

            if self.role == "instructor":
                self.server = TCPServer(self.port)
                self.server.start()

        self._add_system_controls()

        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self._update_operating_time)
        self.clock_timer.start(1000)
        self._update_operating_time()

        container = QWidget()
        container.setLayout(self.layout)
        container.setContentsMargins(0, 0, 0, 0)
        self.setCentralWidget(container)

    def _icon_path(self, file_name: str) -> Path:
        return Path(__file__).resolve().parent / "icons" / file_name

    def _add_system_controls(self):
        control_container = QWidget()
        control_layout = QVBoxLayout(control_container)
        control_layout.setContentsMargins(0, 6, 0, 0)

        action_row = QHBoxLayout()
        action_row.setSpacing(12)
        action_row.setAlignment(Qt.AlignmentFlag.AlignCenter)

        shutdown_btn = QPushButton()
        shutdown_btn.setToolTip("Shutdown")
        shutdown_btn.setIcon(QIcon(str(self._icon_path("shutdown.png"))))
        shutdown_btn.setIconSize(QSize(36, 36))
        shutdown_btn.setFixedSize(72, 72)
        shutdown_btn.setStyleSheet("background-color:#1a1a1a; border:1px solid #333; border-radius:10px; color:white;")
        shutdown_btn.clicked.connect(lambda: self._request_system_action("shutdown"))
        action_row.addWidget(shutdown_btn)

        reboot_btn = QPushButton()
        reboot_btn.setToolTip("Reboot")
        reboot_btn.setIcon(QIcon(str(self._icon_path("reboot.png"))))
        reboot_btn.setIconSize(QSize(36, 36))
        reboot_btn.setFixedSize(72, 72)
        reboot_btn.setStyleSheet("background-color:#1a1a1a; border:1px solid #333; border-radius:10px; color:white;")
        reboot_btn.clicked.connect(lambda: self._request_system_action("reboot"))
        action_row.addWidget(reboot_btn)

        self.clock_label = QLabel("0000:00")
        self.clock_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.clock_label.setStyleSheet("color: white; font-size: 26px; font-weight: bold; min-width: 150px;")
        action_row.addWidget(self.clock_label)

        self.sound_button = QPushButton()
        self.sound_button.setToolTip("Toggle sound")
        self._update_sound_button_icon()
        self.sound_button.setIconSize(QSize(36, 36))
        self.sound_button.setFixedSize(72, 72)
        self.sound_button.setStyleSheet("background-color:#1a1a1a; border:1px solid #333; border-radius:10px; color:white;")
        self.sound_button.clicked.connect(self._toggle_sound_local)
        action_row.addWidget(self.sound_button)

        control_layout.addLayout(action_row)
        self.layout.addWidget(control_container)

    def _update_sound_button_icon(self):
        icon_name = "sound-on.png" if not self._sound_muted else "sound-off.png"
        self.sound_button.setIcon(QIcon(str(self._icon_path(icon_name))))

    def _toggle_sound_local(self):
        self._toggle_sound(force_state=None)
        self._broadcast_system_action("mute" if self._sound_muted else "unmute")

    def _toggle_sound(self, force_state: bool | None = None):
        desired_state = self._sound_muted if force_state is None else force_state
        if force_state is None:
            desired_state = not self._sound_muted

        if desired_state != self._sound_muted:
            self._set_master_volume_toggle()
        self._sound_muted = desired_state
        self._update_sound_button_icon()

    def _set_master_volume_toggle(self):
        if os.name != "nt":
            return
        try:
            user32 = ctypes.windll.user32
            volume_mute_key = 0xAD
            user32.keybd_event(volume_mute_key, 0, 0, 0)
            user32.keybd_event(volume_mute_key, 0, 0x0002, 0)
        except Exception:
            pass

    def _request_system_action(self, action: str):
        self._broadcast_system_action(action)
        self._execute_system_action(action)

    def _broadcast_system_action(self, action: str):
        try:
            if hasattr(self, "server"):
                self.server.broadcast(build_system_action_payload(action))
        except Exception:
            pass

    def _execute_system_action(self, action: str):
        if action == "shutdown":
            try:
                subprocess.run(["shutdown", "/s", "/t", "0"], check=False)
            except Exception:
                pass
        elif action == "reboot":
            try:
                subprocess.run(["shutdown", "/r", "/t", "0"], check=False)
            except Exception:
                pass

    def _handle_system_action(self, action: str, *, is_remote: bool = False):
        if action in {"shutdown", "reboot"}:
            if not is_remote:
                self._request_system_action(action)
            else:
                self._execute_system_action(action)
        elif action in {"mute", "unmute"}:
            self._toggle_sound(force_state=action == "mute")

    def _start_app(self, cmd: str):
        try:
            subprocess.Popen(cmd, shell=True)
        except Exception:
            try:
                subprocess.Popen([cmd])
            except Exception:
                pass

    def _minimize_launcher(self):
        self.showMinimized()

    def make_instructor_launcher(self, cmd: str):
        def _launch_and_broadcast():
            self._start_app(cmd)
            try:
                if hasattr(self, "server"):
                    payload = (json.dumps({"cmd": cmd}) + "\n").encode("utf-8")
                    self.server.broadcast(payload)
            except Exception:
                pass
            self._minimize_launcher()

        return _launch_and_broadcast

    def _handle_remote_payload(self, payload: dict):
        if payload.get("cmd"):
            self._start_app(payload["cmd"])
            self._minimize_launcher()
            return
        if payload.get("action"):
            self._handle_system_action(payload["action"], is_remote=True)
            self._minimize_launcher()

    def handle_remote_launch(self, payload: str | dict):
        if isinstance(payload, str):
            self._start_app(payload)
            self._minimize_launcher()
            return
        self._handle_remote_payload(payload)

    def _update_operating_time(self):
        elapsed = time.monotonic() - self._started_at
        self.clock_label.setText(format_operating_time(elapsed))

    def show_on_monitor(self):
        geom = QGuiApplication.primaryScreen().geometry()
        screens = QGuiApplication.screens()
        if screens:
            for screen in screens:
                geom = geom.united(screen.geometry())
        self.setGeometry(geom)
        self.show()

