from __future__ import annotations

import socket
import time
from queue import Empty
from typing import Any

import pygame

from typing_chase import config
from typing_chase.game_state import GameState, Phase, Role
from typing_chase.networking import JsonLineConnection, NetworkPeer, connect_socket, host_socket


class MenuScreen:
    def __init__(self, status: str = "") -> None:
        self.next_screen = None
        self.should_quit = False
        self.status = status

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN:
            return

        if event.key == pygame.K_h:
            try:
                self.next_screen = HostLobby.host()
            except OSError as exc:
                self.status = f"Host failed: {exc}"
        elif event.key == pygame.K_j:
            self.next_screen = JoinScreen()
        elif event.key == pygame.K_ESCAPE:
            self.should_quit = True

    def update(self) -> None:
        pass

    def draw(self, renderer) -> None:
        renderer.clear()
        renderer.centered("Typing Chase", 130)
        renderer.text("H - Host game", (360, 230))
        renderer.text("J - Join game", (360, 270))
        renderer.text("Escape - Quit", (360, 310))
        if self.status:
            renderer.text(self.status, (260, 370))


class JoinScreen:
    def __init__(self) -> None:
        self.next_screen = None
        self.should_quit = False
        self.host_text = "127.0.0.1"
        self.status = "Enter host IP"

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN:
            return

        if event.key == pygame.K_ESCAPE:
            self.next_screen = MenuScreen()
        elif event.key == pygame.K_BACKSPACE:
            self.host_text = self.host_text[:-1]
        elif event.key == pygame.K_RETURN:
            self._connect()
        elif event.unicode.isdigit() or event.unicode == ".":
            self.host_text += event.unicode

    def _connect(self) -> None:
        try:
            sock = connect_socket(self.host_text, config.NETWORK_PORT)
        except OSError as exc:
            self.status = f"Connection failed: {exc}"
            return

        peer = NetworkPeer(JsonLineConnection(sock))
        peer.start_reader()
        self.next_screen = HostLobby.client(peer)

    def update(self) -> None:
        pass

    def draw(self, renderer) -> None:
        renderer.clear()
        renderer.centered("Join LAN Game", 120)
        renderer.text(f"Host: {self.host_text}", (300, 230))
        renderer.text(self.status, (300, 270))
        renderer.text("Enter - Connect", (300, 330))
        renderer.text("Escape - Menu", (300, 370))


class HostLobby:
    def __init__(
        self,
        *,
        is_host: bool,
        peer: NetworkPeer | None = None,
        server: socket.socket | None = None,
    ) -> None:
        self.is_host = is_host
        self.peer = peer
        self.server = server
        self.next_screen = None
        self.should_quit = False
        self.local_ready = False
        self.remote_ready = False
        self.host_address = local_lan_ip() if is_host else ""
        self.status = "Waiting for client..." if is_host else "Connected. Press Space when ready."

        if self.server is not None:
            self.server.setblocking(False)

    @classmethod
    def host(cls) -> "HostLobby":
        return cls(is_host=True, server=host_socket("", config.NETWORK_PORT))

    @classmethod
    def client(cls, peer: NetworkPeer) -> "HostLobby":
        return cls(is_host=False, peer=peer)

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN:
            return

        if event.key == pygame.K_ESCAPE:
            self._close()
            self.next_screen = MenuScreen()
        elif event.key == pygame.K_SPACE:
            self.local_ready = True
            if self.is_host:
                self._try_start_host_game()
            elif self.peer is not None:
                if self.peer.send({"type": "ready"}):
                    self.status = "Ready. Waiting for host..."
                else:
                    self.peer.close()
                    self.next_screen = MenuScreen("Disconnected from host.")

    def update(self) -> None:
        if self.is_host and self.peer is None:
            self._accept_client()

        if self._peer_disconnected():
            if self.is_host:
                self.peer.close()
                self.peer = None
                self.remote_ready = False
                self.status = "Client disconnected. Waiting for client..."
            else:
                self.peer.close()
                self.next_screen = MenuScreen("Disconnected from host.")
            return

        for message in self._drain_messages():
            if self.is_host and message.get("type") == "ready":
                self.remote_ready = True
                self.status = "Client ready. Press Space to start."
            elif not self.is_host and message.get("type") == "start":
                self.next_screen = NetworkGameScreen.client(self.peer)

    def draw(self, renderer) -> None:
        renderer.clear()
        renderer.centered("LAN Lobby", 120)
        renderer.text(self.status, (270, 230))
        if self.is_host:
            renderer.text(f"Host: {self.host_address}:{config.NETWORK_PORT}", (270, 270))
        renderer.text("Space - Ready / Start", (270, 300))
        renderer.text("Escape - Menu", (270, 340))

    def _accept_client(self) -> None:
        if self.server is None:
            return

        try:
            sock, address = self.server.accept()
        except BlockingIOError:
            return
        except OSError as exc:
            self.status = f"Host error: {exc}"
            return

        sock.setblocking(True)
        self.peer = NetworkPeer(JsonLineConnection(sock))
        self.peer.start_reader()
        self.status = f"Client connected: {address[0]}"

    def _try_start_host_game(self) -> None:
        if self.peer is None:
            self.status = "Waiting for client..."
            return
        if not self.local_ready:
            self.status = "Client ready. Press Space to start."
            return

        if not self.peer.send({"type": "start"}):
            self.peer.close()
            self.peer = None
            self.remote_ready = False
            self.status = "Client disconnected. Waiting for client..."
            return
        self._close_server()
        self.next_screen = NetworkGameScreen.host(self.peer)

    def _peer_disconnected(self) -> bool:
        return self.peer is not None and self.peer.stopped.is_set()

    def _drain_messages(self) -> list[dict[str, Any]]:
        if self.peer is None:
            return []

        messages = []
        while True:
            try:
                messages.append(self.peer.incoming.get_nowait())
            except Empty:
                return messages

    def _close_server(self) -> None:
        if self.server is not None:
            self.server.close()
            self.server = None

    def _close(self) -> None:
        self._close_server()
        if self.peer is not None:
            self.peer.close()


class NetworkGameScreen:
    def __init__(
        self,
        peer: NetworkPeer,
        local_role: Role,
        state: GameState | None = None,
        prompt_index: int = 0,
    ) -> None:
        self.peer = peer
        self.local_role = local_role
        self.state = state
        self.prompt_index = prompt_index
        self.latest_snapshot: dict[str, Any] | None = None
        self.next_screen = None
        self.should_quit = False
        self._last_state_send = 0.0

        if self.state is not None:
            now = time.monotonic()
            self.state.start(now)
            self.latest_snapshot = self.state.to_snapshot(now)

    @classmethod
    def host(cls, peer: NetworkPeer, prompt_index: int = 0) -> "NetworkGameScreen":
        return cls(peer, Role.POLICE, GameState.new_match(prompt_index), prompt_index)

    @classmethod
    def client(cls, peer: NetworkPeer, prompt_index: int = 0) -> "NetworkGameScreen":
        return cls(peer, Role.THIEF, prompt_index=prompt_index)

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN:
            return

        if event.key == pygame.K_ESCAPE:
            self.peer.close()
            self.next_screen = MenuScreen()
            return

        if event.key == pygame.K_r and self._match_has_ended():
            if self.local_role == Role.POLICE:
                self._restart_host_match()
            elif not self.peer.send({"type": "restart_request"}):
                self.peer.close()
                self.next_screen = MenuScreen("Disconnected from match.")
            return

        if event.unicode == "":
            return

        if self.local_role == Role.POLICE and self.state is not None:
            self.state.apply_key(Role.POLICE, event.unicode, time.monotonic())
        elif self.local_role == Role.THIEF:
            if not self.peer.send({"type": "key", "key": event.unicode}):
                self.peer.close()
                self.next_screen = MenuScreen("Disconnected from match.")

    def update(self) -> None:
        if self.peer.stopped.is_set():
            self.peer.close()
            self.next_screen = MenuScreen("Disconnected from match.")
            return

        if self.local_role == Role.POLICE:
            self._update_host()
        else:
            self._update_client()

    def snapshot(self) -> dict[str, Any]:
        if self.latest_snapshot is not None:
            return self.latest_snapshot
        return GameState.new_match().to_snapshot()

    def draw(self, renderer) -> None:
        renderer.draw_game(self.snapshot(), local_role=self.local_role.value)

    def _update_host(self) -> None:
        if self.state is None:
            return

        now = time.monotonic()
        for message in self._drain_messages():
            if message.get("type") == "key":
                self.state.apply_key(Role.THIEF, str(message.get("key", "")), now)
            elif message.get("type") == "restart_request" and self.state.phase.value == "ended":
                self._restart_host_match()
                return

        self.state.update(now)
        self.latest_snapshot = self.state.to_snapshot(now)
        if now - self._last_state_send >= 1.0 / config.STATE_SEND_HZ:
            if not self.peer.send({"type": "state", "game": self.latest_snapshot}):
                self.peer.close()
                self.next_screen = MenuScreen("Disconnected from match.")
                return
            self._last_state_send = now

    def _update_client(self) -> None:
        for message in self._drain_messages():
            if message.get("type") == "state" and isinstance(message.get("game"), dict):
                self.latest_snapshot = message["game"]
                self.prompt_index = int(self.latest_snapshot.get("prompt_index", self.prompt_index))
            elif message.get("type") == "restart" and isinstance(message.get("game"), dict):
                self.latest_snapshot = message["game"]
                self.prompt_index = int(self.latest_snapshot.get("prompt_index", self.prompt_index))

    def _match_has_ended(self) -> bool:
        if self.state is not None:
            return self.state.phase == Phase.ENDED
        return self.snapshot().get("phase") == "ended"

    def _restart_host_match(self) -> None:
        self.prompt_index = (self.prompt_index + 1) % len(config.PROMPTS)
        self.state = GameState.new_match(self.prompt_index)
        now = time.monotonic()
        self.state.start(now)
        self.latest_snapshot = self.state.to_snapshot(now)
        self._last_state_send = 0.0
        if not self.peer.send({"type": "restart", "game": self.latest_snapshot}):
            self.peer.close()
            self.next_screen = MenuScreen("Disconnected from match.")

    def _drain_messages(self) -> list[dict[str, Any]]:
        messages = []
        while True:
            try:
                messages.append(self.peer.incoming.get_nowait())
            except Empty:
                return messages


def local_lan_ip() -> str:
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("8.8.8.8", 80))
        return str(probe.getsockname()[0])
    except OSError:
        return "127.0.0.1"
    finally:
        probe.close()
