import socket

from typing_chase.networking import JsonLineConnection


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
