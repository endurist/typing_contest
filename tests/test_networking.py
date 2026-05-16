from typing_chase.networking import JsonLineConnection, connect_socket, host_socket
import typing_chase.networking as networking
import socket


def test_json_line_connection_sends_and_receives_message():
    left, right = socket.socketpair()
    try:
        sender = JsonLineConnection(left)
        receiver = JsonLineConnection(right)

        sender.send({"type": "key", "key": "a"})

        assert receiver.receive() == {"type": "key", "key": "a"}
    finally:
        left.close()
        right.close()


def test_json_line_connection_buffers_partial_messages():
    left, right = socket.socketpair()
    try:
        right.sendall(b'{"type": "ready"}\n{"type": "key", "key": "b"}\n')
        receiver = JsonLineConnection(left)

        assert receiver.receive() == {"type": "ready"}
        assert receiver.receive() == {"type": "key", "key": "b"}
    finally:
        left.close()
        right.close()


class FakeSocket:
    def __init__(self, *_args):
        self.options = []
        self.bound_to = None
        self.listen_backlog = None
        self.connected_to = None

    def setsockopt(self, *args):
        self.options.append(args)

    def bind(self, address):
        self.bound_to = address

    def listen(self, backlog):
        self.listen_backlog = backlog

    def connect(self, address):
        self.connected_to = address


def test_host_socket_binds_and_listens(monkeypatch):
    sockets = []
    monkeypatch.setattr(networking.socket, "socket", lambda *args: sockets.append(FakeSocket(*args)) or sockets[-1])

    server = host_socket("127.0.0.1", 5050)

    assert server.bound_to == ("127.0.0.1", 5050)
    assert server.listen_backlog == 1
    assert (socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) in server.options


def test_connect_socket_connects_to_address(monkeypatch):
    sockets = []
    monkeypatch.setattr(networking.socket, "socket", lambda *args: sockets.append(FakeSocket(*args)) or sockets[-1])

    client = connect_socket("127.0.0.1", 5050)

    assert client.connected_to == ("127.0.0.1", 5050)
