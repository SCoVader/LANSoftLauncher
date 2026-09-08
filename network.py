import json
import socket
import threading
import time


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
                    conn, _ = self._sock.accept()
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
            for client in list(self._clients):
                try:
                    client.sendall(data)
                except Exception:
                    try:
                        client.close()
                    except Exception:
                        pass
                    to_remove.append(client)
            for client in to_remove:
                if client in self._clients:
                    self._clients.remove(client)

    def close(self):
        self._running = False
        try:
            if self._sock is not None:
                self._sock.close()
        except Exception:
            pass
        with self._lock:
            for client in self._clients:
                try:
                    client.close()
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
                buffer = b""
                while self._running:
                    data = sock.recv(4096)
                    if not data:
                        break
                    buffer += data
                    while b"\n" in buffer:
                        line, buffer = buffer.split(b"\n", 1)
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
                    if sock is not None:
                        sock.close()
                except Exception:
                    pass
            time.sleep(2.0)

    def stop(self):
        self._running = False
