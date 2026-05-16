import pygame
from queue import Empty

from typing_chase.game_state import Role
from typing_chase.screens import HostLobby, JoinScreen, MenuScreen, NetworkGameScreen


class FakePeer:
    def __init__(self, incoming=None):
        self.incoming = incoming or []
        self.sent = []
        self.closed = False

    def send(self, message):
        self.sent.append(message)

    def close(self):
        self.closed = True


class FakeQueue:
    def __init__(self, messages):
        self.messages = list(messages)

    def get_nowait(self):
        if not self.messages:
            raise Empty
        return self.messages.pop(0)


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
