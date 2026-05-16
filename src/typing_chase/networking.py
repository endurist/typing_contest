from __future__ import annotations

import json
import socket
from dataclasses import dataclass, field
from queue import Queue
from threading import Event, Thread
from typing import Any


class ConnectionClosed(RuntimeError):
    pass


class JsonLineConnection:
    def __init__(self, sock: socket.socket) -> None:
        self.sock = sock
        self._buffer = b""

    def send(self, message: dict[str, Any]) -> None:
        payload = json.dumps(message, separators=(",", ":")).encode("utf-8") + b"\n"
        self.sock.sendall(payload)

    def receive(self) -> dict[str, Any]:
        while b"\n" not in self._buffer:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise ConnectionClosed("socket closed")
            self._buffer += chunk

        line, self._buffer = self._buffer.split(b"\n", 1)
        return json.loads(line.decode("utf-8"))


@dataclass
class NetworkPeer:
    connection: JsonLineConnection
    incoming: Queue[dict[str, Any]] = field(default_factory=Queue)
    stopped: Event = field(default_factory=Event)
    error: str | None = None

    def start_reader(self) -> None:
        thread = Thread(target=self._read_loop, daemon=True)
        thread.start()

    def _read_loop(self) -> None:
        while not self.stopped.is_set():
            try:
                self.incoming.put(self.connection.receive())
            except Exception as exc:
                self.error = str(exc)
                self.stopped.set()
                return

    def send(self, message: dict[str, Any]) -> bool:
        try:
            self.connection.send(message)
        except OSError as exc:
            self.error = str(exc)
            self.stopped.set()
            return False
        return True

    def close(self) -> None:
        self.stopped.set()
        try:
            self.connection.sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        self.connection.sock.close()


def host_socket(host: str, port: int) -> socket.socket:
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((host, port))
    server.listen(1)
    return server


def connect_socket(host: str, port: int) -> socket.socket:
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.settimeout(2.0)
    client.connect((host, port))
    client.settimeout(None)
    return client
