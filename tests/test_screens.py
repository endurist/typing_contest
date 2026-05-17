import pygame
from queue import Empty

from typing_chase.game_state import Role
from typing_chase.screens import HostLobby, JoinScreen, MenuScreen, NetworkGameScreen


class FakePeer:
    def __init__(self, incoming=None):
        self.incoming = incoming or []
        self.sent = []
        self.closed = False
        self.stopped = type("Stopped", (), {"is_set": lambda _self: False})()
        self.error = None
        self.send_result = True

    def send(self, message):
        if not self.send_result:
            self.error = "send failed"
            self.stopped = type("Stopped", (), {"is_set": lambda _self: True})()
            return False
        self.sent.append(message)
        return True

    def close(self):
        self.closed = True


class FakeQueue:
    def __init__(self, messages):
        self.messages = list(messages)

    def get_nowait(self):
        if not self.messages:
            raise Empty
        return self.messages.pop(0)


class FakeAcceptedSocket:
    def __init__(self):
        self.blocking_values = []

    def setblocking(self, value):
        self.blocking_values.append(value)


class FakeServerSocket:
    def __init__(self, accepted_socket):
        self.accepted_socket = accepted_socket

    def setblocking(self, value):
        pass

    def accept(self):
        return self.accepted_socket, ("192.168.1.20", 50000)


def key_event(key, unicode=""):
    return pygame.event.Event(pygame.KEYDOWN, key=key, unicode=unicode)


def test_menu_selects_host_and_join_screens(monkeypatch):
    monkeypatch.setattr(HostLobby, "host", classmethod(lambda cls: cls(is_host=True)))
    menu = MenuScreen()

    menu.handle_event(key_event(pygame.K_h, "h"))

    assert isinstance(menu.next_screen, HostLobby)

    menu = MenuScreen()
    menu.handle_event(key_event(pygame.K_j, "j"))

    assert isinstance(menu.next_screen, JoinScreen)


def test_menu_shows_status_when_host_creation_fails(monkeypatch):
    def fail_host(cls):
        raise OSError("port busy")

    monkeypatch.setattr(HostLobby, "host", classmethod(fail_host))
    menu = MenuScreen()

    menu.handle_event(key_event(pygame.K_h, "h"))

    assert menu.next_screen is None
    assert "port busy" in menu.status


def test_host_lobby_has_lan_address(monkeypatch):
    monkeypatch.setattr("typing_chase.screens.local_lan_ip", lambda: "192.168.1.5")

    lobby = HostLobby(is_host=True)

    assert lobby.host_address == "192.168.1.5"


def test_host_accept_sets_client_socket_back_to_blocking(monkeypatch):
    accepted_socket = FakeAcceptedSocket()
    monkeypatch.setattr("typing_chase.screens.NetworkPeer.start_reader", lambda self: None)
    lobby = HostLobby(is_host=True, server=FakeServerSocket(accepted_socket))

    lobby.update()

    assert accepted_socket.blocking_values == [True]
    assert lobby.status == "Client connected: 192.168.1.20"


def test_join_screen_edits_ip_text():
    join = JoinScreen()

    join.handle_event(key_event(pygame.K_BACKSPACE))
    join.handle_event(key_event(pygame.K_8, "8"))
    join.handle_event(key_event(pygame.K_PERIOD, "."))

    assert join.host_text == "127.0.0.8."


def test_host_game_applies_remote_thief_key_and_sends_state():
    peer = FakePeer()
    peer.incoming = FakeQueue([{"type": "key", "key": "t"}])
    game = NetworkGameScreen.host(peer)
    thief_start = game.state.thief.position

    game.update()

    assert game.state.thief.position > thief_start
    assert peer.sent[-1]["type"] == "state"
    assert peer.sent[-1]["game"]["thief"]["position"] == game.state.thief.position


def test_host_starts_after_client_connects_when_space_pressed():
    peer = FakePeer()
    lobby = HostLobby(is_host=True, peer=peer)

    lobby.handle_event(key_event(pygame.K_SPACE, " "))

    assert isinstance(lobby.next_screen, NetworkGameScreen)
    assert peer.sent == [{"type": "start"}]


def test_client_ready_send_failure_returns_to_menu():
    peer = FakePeer()
    peer.send_result = False
    lobby = HostLobby.client(peer)

    lobby.handle_event(key_event(pygame.K_SPACE, " "))

    assert isinstance(lobby.next_screen, MenuScreen)
    assert "Disconnected" in lobby.next_screen.status
    assert peer.closed is True


def test_host_lobby_disconnect_waits_for_replacement():
    peer = FakePeer()
    peer.stopped = type("Stopped", (), {"is_set": lambda _self: True})()
    lobby = HostLobby(is_host=True, peer=peer)

    lobby.update()

    assert lobby.peer is None
    assert "Waiting for client" in lobby.status
    assert peer.closed is True


def test_client_game_sends_keys_without_local_mutation_and_accepts_state():
    peer = FakePeer()
    peer.incoming = FakeQueue(
        [
            {
                "type": "state",
                "game": {
                    "phase": "playing",
                    "timer_remaining": 88,
                    "winner": None,
                    "end_reason": None,
                    "police": {"position": 12, "prompt": "abc", "cursor": 1},
                    "thief": {"position": 222, "prompt": "abc", "cursor": 2},
                },
            }
        ]
    )
    game = NetworkGameScreen.client(peer)

    game.handle_event(key_event(pygame.K_a, "a"))
    game.update()

    assert peer.sent == [{"type": "key", "key": "a"}]
    assert game.snapshot()["thief"]["position"] == 222
    assert game.local_role == Role.THIEF


def test_client_game_send_failure_returns_to_menu():
    peer = FakePeer()
    peer.incoming = FakeQueue([])
    peer.send_result = False
    game = NetworkGameScreen.client(peer)

    game.handle_event(key_event(pygame.K_a, "a"))

    assert isinstance(game.next_screen, MenuScreen)
    assert "Disconnected" in game.next_screen.status
    assert peer.closed is True


def test_host_game_state_send_failure_returns_to_menu():
    peer = FakePeer()
    peer.incoming = FakeQueue([])
    peer.send_result = False
    game = NetworkGameScreen.host(peer)
    game._last_state_send = -999.0

    game.update()

    assert isinstance(game.next_screen, MenuScreen)
    assert "Disconnected" in game.next_screen.status
    assert peer.closed is True


def test_client_game_stopped_peer_returns_to_menu_and_closes():
    peer = FakePeer()
    peer.incoming = FakeQueue([])
    peer.stopped = type("Stopped", (), {"is_set": lambda _self: True})()
    game = NetworkGameScreen.client(peer)

    game.update()

    assert isinstance(game.next_screen, MenuScreen)
    assert peer.closed is True
