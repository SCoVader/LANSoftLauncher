import json
import socket
import threading
import time

from network import TCPClient, TCPServer


def test_discovery_and_tcp_connections_require_matching_system_name():
    server = TCPServer(port=0, host="127.0.0.1", system_name="complex1")
    server.start()
    try:
        assert server._ready.wait(2)

        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as discovery_socket:
            discovery_socket.settimeout(0.1)
            discovery_socket.sendto(
                json.dumps(
                    {"type": "discover", "system_name": "another"}
                ).encode("utf-8"),
                ("127.0.0.1", server.port),
            )
            try:
                discovery_socket.recvfrom(1024)
            except socket.timeout:
                pass
            else:
                raise AssertionError("server responded to a different system_name")

        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as discovery_socket:
            discovery_socket.settimeout(2)
            discovery_socket.sendto(
                json.dumps(
                    {"type": "discover", "system_name": "complex1"}
                ).encode("utf-8"),
                ("127.0.0.1", server.port),
            )
            response, address = discovery_socket.recvfrom(1024)

        assert json.loads(response.decode("utf-8")) == {
            "type": "server",
            "system_name": "complex1",
            "port": server.port,
        }
        assert address[0] == "127.0.0.1"

        with socket.create_connection(("127.0.0.1", server.port), timeout=2) as client:
            client.sendall(b'{"type":"authenticate","system_name":"another"}\n')
            assert client.recv(1) == b""

        with socket.create_connection(("127.0.0.1", server.port), timeout=2) as client:
            client.sendall(b'{"type":"authenticate","system_name":"complex1"}\n')
            response = client.recv(128)
            assert json.loads(response.decode("utf-8")) == {
                "type": "authenticated"
            }
            deadline = time.monotonic() + 2
            while time.monotonic() < deadline:
                with server._lock:
                    if server._clients:
                        break
                time.sleep(0.01)
            server.broadcast(b"accepted\n")
            assert client.recv(32) == b"accepted\n"
    finally:
        server.close()
        server.join(timeout=2)


def test_client_reports_connection_and_disconnection():
    server = TCPServer(port=0, host="127.0.0.1", system_name="complex1")
    server.start()
    assert server._ready.wait(2)

    states = []
    payloads = []
    connected = threading.Event()
    disconnected = threading.Event()

    def on_connection_change(is_connected):
        states.append(is_connected)
        (connected if is_connected else disconnected).set()

    client = TCPClient(
        "127.0.0.1",
        server.port,
        payloads.append,
        system_name="complex1",
        connection_callback=on_connection_change,
    )
    client.start()
    try:
        assert connected.wait(2)
        assert states == [True]

        server.close()
        server.join(timeout=2)
        assert disconnected.wait(2)
        assert states == [True, False]
    finally:
        client.stop()
        client.join(timeout=2)
        server.close()
