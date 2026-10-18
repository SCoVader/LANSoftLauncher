import json
import select
import socket
import threading
import time


class TCPServer(threading.Thread):
    def __init__(self, port: int = 8765, host: str = "0.0.0.0", system_name: str = "complex1"):
        super().__init__(daemon=True)
        self.port = port
        self.host = host
        self.system_name = system_name
        self._sock = None
        self._discovery_sock = None
        self._clients = []
        self._lock = threading.Lock()
        self._running = True
        self._ready = threading.Event()

    def run(self):
        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._sock.bind((self.host, self.port))
            self._sock.listen()
            self.port = self._sock.getsockname()[1]

            self._discovery_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._discovery_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._discovery_sock.bind(("", self.port))
            discovery_sock = self._discovery_sock
            self._ready.set()

            while self._running:
                readable, _, _ = select.select([self._sock, discovery_sock], [], [], 0.5)
                for ready_sock in readable:
                    if ready_sock is discovery_sock:
                        self._respond_to_discovery(discovery_sock)
                        continue

                    connection, _ = self._sock.accept()
                    connection.settimeout(2.0)
                    if self._authenticate(connection):
                        connection.settimeout(None)
                        with self._lock:
                            self._clients.append(connection)
                    else:
                        connection.close()
        except OSError:
            if self._running:
                raise
        finally:
            self._ready.set()
            self.close()

    def _respond_to_discovery(self, discovery_sock: socket.socket):
        try:
            data, address = discovery_sock.recvfrom(1024)
            request = json.loads(data.decode("utf-8"))
            if (
                isinstance(request, dict)
                and request.get("type") == "discover"
                and request.get("system_name") == self.system_name
            ):
                response = json.dumps(
                    {
                        "type": "server",
                        "system_name": self.system_name,
                        "port": self.port,
                    }
                ).encode("utf-8")
                discovery_sock.sendto(response, address)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            pass

    def _authenticate(self, connection: socket.socket) -> bool:
        try:
            data = bytearray()
            while len(data) < 1024:
                chunk = connection.recv(1024 - len(data))
                if not chunk:
                    return False
                data.extend(chunk)
                if b"\n" in chunk:
                    message = bytes(data).split(b"\n", 1)[0]
                    payload = json.loads(message.decode("utf-8"))
                    return (
                        isinstance(payload, dict)
                        and payload.get("type") == "authenticate"
                        and payload.get("system_name") == self.system_name
                    )
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return False
        return False

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
        try:
            if self._discovery_sock is not None:
                self._discovery_sock.close()
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
    def __init__(self, host: str, port: int, callback, system_name: str = "complex1"):
        super().__init__(daemon=True)
        self.host = host
        self.port = port
        self.callback = callback
        self.system_name = system_name
        self._running = True

    def _discover_server(self):
        request = json.dumps(
            {"type": "discover", "system_name": self.system_name}
        ).encode("utf-8")
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as discovery_sock:
            discovery_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            discovery_sock.settimeout(1.0)
            discovery_sock.sendto(request, ("255.255.255.255", self.port))
            while self._running:
                try:
                    data, address = discovery_sock.recvfrom(1024)
                except socket.timeout:
                    return None
                try:
                    response = json.loads(data.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    continue
                if (
                    isinstance(response, dict)
                    and response.get("type") == "server"
                    and response.get("system_name") == self.system_name
                    and isinstance(response.get("port"), int)
                ):
                    return address[0], response["port"]
        return None

    def run(self):
        while self._running:
            sock = None
            try:
                server_address = (self.host, self.port) if self.host else self._discover_server()
                if server_address is None:
                    time.sleep(2.0)
                    continue

                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5.0)
                sock.connect(server_address)
                authentication = json.dumps(
                    {"type": "authenticate", "system_name": self.system_name}
                )
                sock.sendall((authentication + "\n").encode("utf-8"))
                sock.settimeout(1.0)
                buffer = b""
                while self._running:
                    try:
                        data = sock.recv(4096)
                    except socket.timeout:
                        continue
                    if not data:
                        break
                    buffer += data
                    while b"\n" in buffer:
                        line, buffer = buffer.split(b"\n", 1)
                        try:
                            payload = json.loads(line.decode("utf-8"))
                            if payload.get("cmd"):
                                self.callback({"cmd": payload["cmd"]})
                            elif payload.get("action"):
                                self.callback({"action": payload["action"]})
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
            if self._running:
                time.sleep(2.0)

    def stop(self):
        self._running = False
