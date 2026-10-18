import json
import socket
import time

from network import TCPServer


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
