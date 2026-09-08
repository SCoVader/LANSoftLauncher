import sys
import json
import subprocess
import threading
import socket
import time
from pathlib import Path
from PySide6.QtWidgets import QApplication, QMainWindow, QLabel, QPushButton, QVBoxLayout, QWidget
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QGuiApplication


class TCPServer(threading.Thread):
    def __init__(self, port: int = 8765, host: str = "0.0.0.0"):
        super().__init__(daemon=True)
        self.port = port
        self.host = host
        self._sock = None
        self._clients = []
        self._lock = threading.Lock()
        self._running = True

    def run(self):
        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._sock.bind((self.host, self.port))
            self._sock.listen()
            self._sock.settimeout(1.0)
            while self._running:
                try:
                    conn, addr = self._sock.accept()
                    conn.setblocking(True)
                    with self._lock:
                        self._clients.append(conn)
                except socket.timeout:
                    continue
                except Exception:
                    break
        finally:
            self.close()

    def broadcast(self, data: bytes):
        with self._lock:
            to_remove = []
            for c in list(self._clients):
                try:
                    c.sendall(data)
                except Exception:
                    try:
                        c.close()
                    except Exception:
                        pass
                    to_remove.append(c)
            for r in to_remove:
                if r in self._clients:
                    self._clients.remove(r)

    def close(self):
        self._running = False
        try:
            if self._sock:
                self._sock.close()
        except Exception:
            pass
        with self._lock:
            for c in self._clients:
                try:
                    c.close()
                except Exception:
                    pass
            self._clients.clear()


class TCPClient(threading.Thread):
    def __init__(self, host: str, port: int, callback):
        super().__init__(daemon=True)
        self.host = host
        self.port = port
        self.callback = callback
        self._running = True

    def run(self):
        if not self.host:
            return
        while self._running:
            sock = None
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5.0)
                sock.connect((self.host, self.port))
                sock.settimeout(None)
                buf = b""
                while self._running:
                    data = sock.recv(4096)
                    if not data:
                        break
                    buf += data
                    while b"\n" in buf:
                        line, buf = buf.split(b"\n", 1)
                        try:
                            payload = json.loads(line.decode("utf-8"))
                            cmd = payload.get("cmd")
                            if cmd:
                                self.callback(cmd)
                        except Exception:
                            pass
            except Exception:
                pass
            finally:
                try:
                    if sock:
                        sock.close()
                except Exception:
                    pass
            # Retry after a short delay
            time.sleep(2.0)

    def stop(self):
        self._running = False

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kiosk Launcher")
        
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.config_path = Path(__file__).parent / "apps.json"
        self.config = self.load_config()
        self.apps = self.config.get("apps", [])
        self.role = self.config.get("role", "standalone")
        self.server_host = self.config.get("server_host", "")
        self.port = int(self.config.get("port", 8765))

        # Black background, centered buttons
        self.setStyleSheet("background-color: black;")

        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.label = QLabel("", alignment=Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("color: white; font-size: 18px;")
        # Role behaviour: instructor shows buttons, listener waits for instructions
        if self.role == "listener":
            self.label.setText("Waiting for instructions...")
            # Start client thread to listen for instructions
            self.client = TCPClient(self.server_host, self.port, self.handle_remote_launch)
            self.client.start()
        else:
            # Create a button for each configured app (instructor or standalone)
            for entry in self.apps:
                text = entry.get("name", "Launch")
                cmd = entry.get("cmd", "")
                btn = QPushButton(text)
                btn.setFixedSize(420, 140)
                btn.setStyleSheet("font-size:24px; background-color:#222; color: white; border-radius:8px;")
                btn.clicked.connect(self.make_instructor_launcher(cmd))
                layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)

            # If instructor role, start TCP server to accept listeners
            if self.role == "instructor":
                self.server = TCPServer(self.port)
                self.server.start()

        # Allow Esc to quit
        self.shortcut_quit = QApplication.instance()

        container = QWidget()
        container.setLayout(layout)
        container.setContentsMargins(0, 0, 0, 0)
        self.setCentralWidget(container)

    def load_apps(self):
        # (deprecated) kept for backward compat
        return []

    def load_config(self):
        default = {
            "role": "standalone",
            "server_host": "",
            "port": 8765,
            "apps": [
                {"name": "Notepad", "cmd": "notepad.exe"},
                {"name": "Calculator", "cmd": "calc.exe"},
                {"name": "Paint", "cmd": "mspaint.exe"}
            ]
        }
        try:
            if self.config_path.exists():
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Accept either list (legacy) or dict (new)
                    if isinstance(data, dict):
                        return {**default, **data}
                    elif isinstance(data, list) and data:
                        default["apps"] = data
                        return default
        except Exception:
            pass
        # Write default config if missing
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

    def make_instructor_launcher(self, cmd):
        def _launch_and_broadcast():
            # Launch locally
            try:
                subprocess.Popen(cmd, shell=True)
            except Exception:
                try:
                    subprocess.Popen([cmd])
                except Exception:
                    pass
            # Broadcast to connected listeners if server running
            try:
                if hasattr(self, "server"):
                    msg = json.dumps({"cmd": cmd}) + "\n"
                    self.server.broadcast(msg.encode("utf-8"))
            except Exception:
                pass
            QTimer.singleShot(150, QApplication.quit)
        return _launch_and_broadcast

    def handle_remote_launch(self, cmd: str):
        # Called by client thread when an instruction arrives
        try:
            subprocess.Popen(cmd, shell=True)
        except Exception:
            try:
                subprocess.Popen([cmd])
            except Exception:
                pass
        QTimer.singleShot(150, QApplication.quit)

    def on_button_click(self):
        self.label.setText("Button Clicked!")

if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = MainWindow()

    geom = QGuiApplication.primaryScreen().geometry()
    screens = QGuiApplication.screens()
    if screens:
        for screen in screens:
            geom = geom.united(screen.geometry())
    window.setGeometry(geom)
    
    
    window.show()
    sys.exit(app.exec())