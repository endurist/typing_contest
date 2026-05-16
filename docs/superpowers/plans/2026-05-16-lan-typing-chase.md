# LAN Typing Chase Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a playable Python/Pygame LAN typing chase MVP where one computer hosts as police and another joins as thief on the same Wi-Fi.

**Architecture:** Keep game rules pure and testable, then wrap them with a small TCP JSON-lines networking layer and a Pygame shell. The host owns authoritative game state; the client sends key events and renders host snapshots.

**Tech Stack:** Python 3.11+, Pygame, standard-library sockets/threading/queue/json, pytest.

---

## File Structure

- `pyproject.toml`: project metadata, pytest config, runtime dependencies.
- `README.md`: setup, run, host/join instructions.
- `src/typing_chase/__init__.py`: package marker and version.
- `src/typing_chase/config.py`: screen, gameplay, and network constants.
- `src/typing_chase/typing_logic.py`: prompt progress and mistake penalty logic.
- `src/typing_chase/game_state.py`: match phases, positions, timer, win conditions, serializable snapshots.
- `src/typing_chase/networking.py`: TCP host/client classes and newline-delimited JSON framing.
- `src/typing_chase/renderer.py`: Pygame drawing helpers.
- `src/typing_chase/screens.py`: menu, lobby, countdown, gameplay, result screen state machine.
- `src/typing_chase/main.py`: CLI entry point and Pygame loop.
- `tests/test_typing_logic.py`: prompt behavior tests.
- `tests/test_game_state.py`: movement and win-condition tests.
- `tests/test_networking.py`: JSON framing tests using socket pairs.

## Task 1: Project Skeleton

**Files:**
- Create: `pyproject.toml`
- Create: `README.md`
- Create: `src/typing_chase/__init__.py`
- Create: `src/typing_chase/config.py`

- [ ] **Step 1: Create package metadata**

Add `pyproject.toml`:

```toml
[project]
name = "typing-chase"
version = "0.1.0"
description = "LAN two-player typing chase game"
requires-python = ">=3.11"
dependencies = [
  "pygame>=2.5.0",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.0.0",
]

[project.scripts]
typing-chase = "typing_chase.main:main"

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
```

- [ ] **Step 2: Add package marker**

Add `src/typing_chase/__init__.py`:

```python
"""LAN typing chase game."""

__version__ = "0.1.0"
```

- [ ] **Step 3: Add configuration constants**

Add `src/typing_chase/config.py`:

```python
from __future__ import annotations

SCREEN_WIDTH = 960
SCREEN_HEIGHT = 540
FPS = 60

NETWORK_PORT = 5050
STATE_SEND_HZ = 20
SOCKET_TIMEOUT_SECONDS = 0.2

TRACK_LENGTH = 1000.0
START_GAP = 180.0
CATCH_DISTANCE = 28.0
MOVE_PER_CHAR = 8.0
MISTAKE_PENALTY_SECONDS = 0.35
ROUND_SECONDS = 90.0
COUNTDOWN_SECONDS = 3.0

PROMPTS = [
    "the city is quiet tonight",
    "keep your eyes on the road",
    "fast fingers win the chase",
    "never stop before the finish",
]
```

- [ ] **Step 4: Add README**

Add `README.md`:

```markdown
# Typing Chase

A two-player LAN typing chase game built with Python and Pygame.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Run

```bash
typing-chase
```

One computer chooses **Host Game** and shares the displayed LAN IP.
The second computer chooses **Join Game** and enters that IP.

## Test

```bash
pytest
```
```

- [ ] **Step 5: Run import check**

Run: `python -m pytest -q`

Expected: pytest runs and reports no tests collected or all existing tests pass.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml README.md src/typing_chase/__init__.py src/typing_chase/config.py
git commit -m "chore: add project skeleton"
```

## Task 2: Typing Logic

**Files:**
- Create: `src/typing_chase/typing_logic.py`
- Create: `tests/test_typing_logic.py`

- [ ] **Step 1: Write failing tests**

Add `tests/test_typing_logic.py`:

```python
from typing_chase.typing_logic import TypingProgress


def test_correct_character_advances_cursor_and_position_delta():
    progress = TypingProgress(prompt="abc", move_per_char=8.0, mistake_penalty_seconds=0.35)

    result = progress.handle_key("a", now=0.0)

    assert result.correct is True
    assert result.move_delta == 8.0
    assert progress.cursor == 1
    assert progress.penalty_until == 0.0


def test_wrong_character_sets_penalty_and_does_not_advance():
    progress = TypingProgress(prompt="abc", move_per_char=8.0, mistake_penalty_seconds=0.35)

    result = progress.handle_key("z", now=1.0)

    assert result.correct is False
    assert result.move_delta == 0.0
    assert progress.cursor == 0
    assert progress.penalty_until == 1.35


def test_input_during_penalty_is_ignored():
    progress = TypingProgress(prompt="abc", move_per_char=8.0, mistake_penalty_seconds=0.35)
    progress.handle_key("z", now=1.0)

    result = progress.handle_key("a", now=1.1)

    assert result.correct is False
    assert result.ignored is True
    assert result.move_delta == 0.0
    assert progress.cursor == 0


def test_completing_prompt_wraps_to_next_prompt():
    progress = TypingProgress(prompt="ab", move_per_char=8.0, mistake_penalty_seconds=0.35)

    progress.handle_key("a", now=0.0)
    result = progress.handle_key("b", now=0.1)

    assert result.completed_prompt is True
    assert progress.cursor == 0
```

- [ ] **Step 2: Run tests and verify failure**

Run: `pytest tests/test_typing_logic.py -q`

Expected: FAIL with `ModuleNotFoundError` or missing `TypingProgress`.

- [ ] **Step 3: Implement typing logic**

Add `src/typing_chase/typing_logic.py`:

```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class KeyResult:
    correct: bool
    move_delta: float
    ignored: bool = False
    completed_prompt: bool = False


@dataclass
class TypingProgress:
    prompt: str
    move_per_char: float
    mistake_penalty_seconds: float
    cursor: int = 0
    penalty_until: float = 0.0

    def handle_key(self, key: str, now: float) -> KeyResult:
        if now < self.penalty_until:
            return KeyResult(correct=False, move_delta=0.0, ignored=True)

        normalized = key.lower()
        expected = self.prompt[self.cursor].lower()
        if normalized != expected:
            self.penalty_until = round(now + self.mistake_penalty_seconds, 6)
            return KeyResult(correct=False, move_delta=0.0)

        self.cursor += 1
        completed = self.cursor >= len(self.prompt)
        if completed:
            self.cursor = 0
        return KeyResult(correct=True, move_delta=self.move_per_char, completed_prompt=completed)
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_typing_logic.py -q`

Expected: `4 passed`.

- [ ] **Step 5: Commit**

```bash
git add src/typing_chase/typing_logic.py tests/test_typing_logic.py
git commit -m "feat: add typing progress logic"
```

## Task 3: Game State Rules

**Files:**
- Create: `src/typing_chase/game_state.py`
- Create: `tests/test_game_state.py`

- [ ] **Step 1: Write failing tests**

Add `tests/test_game_state.py`:

```python
from typing_chase.game_state import GameState, Phase, Role


def test_initial_state_places_thief_ahead():
    state = GameState.new_match()

    assert state.police.position == 0.0
    assert state.thief.position == 180.0
    assert state.phase == Phase.LOBBY


def test_police_moves_on_correct_key():
    state = GameState.new_match()
    state.phase = Phase.PLAYING

    state.apply_key(Role.POLICE, "t", now=0.0)

    assert state.police.position == 8.0
    assert state.thief.position == 180.0


def test_police_wins_when_close_enough():
    state = GameState.new_match()
    state.phase = Phase.PLAYING
    state.police.position = 160.0
    state.thief.position = 188.0

    state.update(now=1.0)

    assert state.phase == Phase.ENDED
    assert state.winner == Role.POLICE
    assert state.end_reason == "caught"


def test_thief_wins_at_escape_line():
    state = GameState.new_match()
    state.phase = Phase.PLAYING
    state.thief.position = 1000.0

    state.update(now=1.0)

    assert state.phase == Phase.ENDED
    assert state.winner == Role.THIEF
    assert state.end_reason == "escaped"


def test_thief_wins_when_timer_expires():
    state = GameState.new_match()
    state.phase = Phase.PLAYING
    state.started_at = 10.0

    state.update(now=100.0)

    assert state.phase == Phase.ENDED
    assert state.winner == Role.THIEF
    assert state.end_reason == "timeout"


def test_snapshot_round_trips_basic_state():
    state = GameState.new_match()
    state.phase = Phase.PLAYING
    state.police.position = 12.0

    snapshot = state.to_snapshot()

    assert snapshot["phase"] == "playing"
    assert snapshot["police"]["position"] == 12.0
    assert snapshot["thief"]["position"] == 180.0
```

- [ ] **Step 2: Run tests and verify failure**

Run: `pytest tests/test_game_state.py -q`

Expected: FAIL with missing `GameState`.

- [ ] **Step 3: Implement game state**

Add `src/typing_chase/game_state.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from typing_chase import config
from typing_chase.typing_logic import TypingProgress


class Phase(str, Enum):
    LOBBY = "lobby"
    COUNTDOWN = "countdown"
    PLAYING = "playing"
    ENDED = "ended"


class Role(str, Enum):
    POLICE = "police"
    THIEF = "thief"


@dataclass
class PlayerState:
    role: Role
    position: float
    typing: TypingProgress


@dataclass
class GameState:
    phase: Phase
    police: PlayerState
    thief: PlayerState
    started_at: float | None = None
    winner: Role | None = None
    end_reason: str | None = None

    @classmethod
    def new_match(cls) -> "GameState":
        prompt = config.PROMPTS[0]
        return cls(
            phase=Phase.LOBBY,
            police=PlayerState(
                role=Role.POLICE,
                position=0.0,
                typing=TypingProgress(prompt, config.MOVE_PER_CHAR, config.MISTAKE_PENALTY_SECONDS),
            ),
            thief=PlayerState(
                role=Role.THIEF,
                position=config.START_GAP,
                typing=TypingProgress(prompt, config.MOVE_PER_CHAR, config.MISTAKE_PENALTY_SECONDS),
            ),
        )

    def start(self, now: float) -> None:
        self.phase = Phase.PLAYING
        self.started_at = now

    def apply_key(self, role: Role, key: str, now: float) -> None:
        if self.phase != Phase.PLAYING or len(key) != 1:
            return

        player = self.police if role == Role.POLICE else self.thief
        result = player.typing.handle_key(key, now)
        player.position += result.move_delta

    def update(self, now: float) -> None:
        if self.phase != Phase.PLAYING:
            return

        if self.police.position + config.CATCH_DISTANCE >= self.thief.position:
            self._end(Role.POLICE, "caught")
            return

        if self.thief.position >= config.TRACK_LENGTH:
            self._end(Role.THIEF, "escaped")
            return

        if self.started_at is not None and now - self.started_at >= config.ROUND_SECONDS:
            self._end(Role.THIEF, "timeout")

    def _end(self, winner: Role, reason: str) -> None:
        self.phase = Phase.ENDED
        self.winner = winner
        self.end_reason = reason

    def timer_remaining(self, now: float) -> float:
        if self.started_at is None:
            return config.ROUND_SECONDS
        return max(0.0, config.ROUND_SECONDS - (now - self.started_at))

    def to_snapshot(self, now: float | None = None) -> dict:
        current_time = 0.0 if now is None else now
        return {
            "phase": self.phase.value,
            "timer_remaining": self.timer_remaining(current_time),
            "winner": None if self.winner is None else self.winner.value,
            "end_reason": self.end_reason,
            "police": self._player_snapshot(self.police),
            "thief": self._player_snapshot(self.thief),
        }

    @staticmethod
    def _player_snapshot(player: PlayerState) -> dict:
        return {
            "role": player.role.value,
            "position": player.position,
            "prompt": player.typing.prompt,
            "cursor": player.typing.cursor,
            "penalty_until": player.typing.penalty_until,
        }
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_game_state.py tests/test_typing_logic.py -q`

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/typing_chase/game_state.py tests/test_game_state.py
git commit -m "feat: add authoritative game state"
```

## Task 4: Networking Message Framing

**Files:**
- Create: `src/typing_chase/networking.py`
- Create: `tests/test_networking.py`

- [ ] **Step 1: Write failing tests**

Add `tests/test_networking.py`:

```python
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
```

- [ ] **Step 2: Run tests and verify failure**

Run: `pytest tests/test_networking.py -q`

Expected: FAIL with missing `JsonLineConnection`.

- [ ] **Step 3: Implement JSON line connection**

Add `src/typing_chase/networking.py`:

```python
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

    def send(self, message: dict[str, Any]) -> None:
        self.connection.send(message)

    def close(self) -> None:
        self.stopped.set()
        self.connection.sock.close()
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_networking.py -q`

Expected: `2 passed`.

- [ ] **Step 5: Commit**

```bash
git add src/typing_chase/networking.py tests/test_networking.py
git commit -m "feat: add json line networking"
```

## Task 5: Pygame Rendering and Screens

**Files:**
- Create: `src/typing_chase/renderer.py`
- Create: `src/typing_chase/screens.py`
- Create: `src/typing_chase/main.py`

- [ ] **Step 1: Add renderer**

Add `src/typing_chase/renderer.py`:

```python
from __future__ import annotations

import pygame

from typing_chase import config

BLUE = (35, 95, 191)
DARK = (34, 34, 34)
ROAD = (217, 222, 231)
TEXT = (31, 47, 67)
WHITE = (250, 252, 255)
RED = (190, 57, 57)


class Renderer:
    def __init__(self, screen: pygame.Surface) -> None:
        self.screen = screen
        self.font = pygame.font.SysFont("arial", 24)
        self.large = pygame.font.SysFont("arial", 38, bold=True)

    def clear(self) -> None:
        self.screen.fill((238, 243, 247))

    def text(self, value: str, pos: tuple[int, int], color: tuple[int, int, int] = TEXT) -> None:
        self.screen.blit(self.font.render(value, True, color), pos)

    def centered(self, value: str, y: int) -> None:
        surface = self.large.render(value, True, TEXT)
        rect = surface.get_rect(center=(config.SCREEN_WIDTH // 2, y))
        self.screen.blit(surface, rect)

    def draw_game(self, snapshot: dict, local_role: str) -> None:
        self.clear()
        self.text(f"You are: {local_role}", (24, 20))
        self.text(f"Time: {snapshot['timer_remaining']:.0f}", (420, 20))

        road = pygame.Rect(60, 120, 840, 150)
        pygame.draw.rect(self.screen, ROAD, road)
        pygame.draw.rect(self.screen, (94, 113, 138), road, 3)
        pygame.draw.line(self.screen, (94, 113, 138), (860, 120), (860, 270), 3)

        police_x = self._track_to_screen(snapshot["police"]["position"])
        thief_x = self._track_to_screen(snapshot["thief"]["position"])
        pygame.draw.circle(self.screen, BLUE, (police_x, 195), 20)
        pygame.draw.circle(self.screen, DARK, (thief_x, 195), 20)
        self.text("P", (police_x - 7, 181), WHITE)
        self.text("T", (thief_x - 7, 181), WHITE)

        self._draw_prompt_panel("Police", snapshot["police"], 330)
        self._draw_prompt_panel("Thief", snapshot["thief"], 420)

        if snapshot["phase"] == "ended":
            self.centered(f"{snapshot['winner']} wins: {snapshot['end_reason']}", 300)

    def _track_to_screen(self, position: float) -> int:
        return int(60 + min(position / config.TRACK_LENGTH, 1.0) * 800)

    def _draw_prompt_panel(self, label: str, player: dict, y: int) -> None:
        rect = pygame.Rect(60, y, 840, 68)
        pygame.draw.rect(self.screen, WHITE, rect)
        pygame.draw.rect(self.screen, (151, 175, 208), rect, 2)
        prompt = player["prompt"]
        cursor = player["cursor"]
        self.text(f"{label}: {prompt[:cursor]}", (76, y + 12), BLUE)
        self.text(prompt[cursor:], (76 + min(cursor * 12, 520), y + 12), TEXT)
```

- [ ] **Step 2: Add simple local screen flow**

Add `src/typing_chase/screens.py`:

```python
from __future__ import annotations

import time

import pygame

from typing_chase.game_state import GameState, Phase, Role


class LocalPreviewGame:
    def __init__(self) -> None:
        self.state = GameState.new_match()
        self.state.start(time.monotonic())
        self.local_role = Role.POLICE

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN or event.unicode == "":
            return
        self.state.apply_key(self.local_role, event.unicode, time.monotonic())

    def update(self) -> None:
        self.state.update(time.monotonic())

    def snapshot(self) -> dict:
        return self.state.to_snapshot(time.monotonic())
```

- [ ] **Step 3: Add runnable Pygame entry point**

Add `src/typing_chase/main.py`:

```python
from __future__ import annotations

import pygame

from typing_chase import config
from typing_chase.renderer import Renderer
from typing_chase.screens import LocalPreviewGame


def main() -> None:
    pygame.init()
    screen = pygame.display.set_mode((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
    pygame.display.set_caption("Typing Chase")
    clock = pygame.time.Clock()
    renderer = Renderer(screen)
    game = LocalPreviewGame()

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            else:
                game.handle_event(event)

        game.update()
        renderer.draw_game(game.snapshot(), local_role=game.local_role.value)
        pygame.display.flip()
        clock.tick(config.FPS)

    pygame.quit()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run automated tests**

Run: `pytest -q`

Expected: all tests pass.

- [ ] **Step 5: Manually run local preview**

Run: `python -m typing_chase.main`

Expected: a Pygame window opens with the road, police, thief, timer, and typing panels. Typing the prompt moves the police.

- [ ] **Step 6: Commit**

```bash
git add src/typing_chase/renderer.py src/typing_chase/screens.py src/typing_chase/main.py
git commit -m "feat: add pygame preview"
```

## Task 6: Host and Join LAN Gameplay

**Files:**
- Modify: `src/typing_chase/networking.py`
- Modify: `src/typing_chase/screens.py`
- Modify: `src/typing_chase/main.py`

- [ ] **Step 1: Extend networking with host/client connection helpers**

Append to `src/typing_chase/networking.py`:

```python
def host_socket(host: str, port: int) -> socket.socket:
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((host, port))
    server.listen(1)
    return server


def connect_socket(host: str, port: int) -> socket.socket:
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((host, port))
    return client
```

- [ ] **Step 2: Replace local preview with mode-aware app states**

Implement `MenuScreen`, `HostLobby`, `JoinScreen`, and `NetworkGameScreen` in `src/typing_chase/screens.py`. Use this behavior contract:

```python
# Menu keys:
# H = host game
# J = join game
# Escape = quit
#
# Join screen:
# numeric keys, dots, and backspace edit IP text
# Enter connects
#
# Lobby:
# Host waits for one client, then starts match when Space is pressed
# Client sends {"type": "ready"} when Space is pressed
#
# Gameplay:
# Host applies local police keys and remote thief keys to GameState
# Client sends {"type": "key", "key": event.unicode}
# Host sends {"type": "state", "game": state.to_snapshot(now)}
# Client renders latest snapshot
```

Use the existing `JsonLineConnection` and `NetworkPeer` classes. Keep the host authoritative: the client never mutates positions locally.

- [ ] **Step 3: Update main loop to delegate to current screen**

Modify `src/typing_chase/main.py` so the current screen object handles:

```python
screen_state.handle_event(event)
screen_state.update()
screen_state.draw(renderer)
screen_state = screen_state.next_screen or screen_state
```

- [ ] **Step 4: Run automated tests**

Run: `pytest -q`

Expected: all tests pass.

- [ ] **Step 5: Manual two-process test on one machine**

Open two terminals.

Terminal 1:

```bash
python -m typing_chase.main
```

Choose Host.

Terminal 2:

```bash
python -m typing_chase.main
```

Choose Join and connect to `127.0.0.1`.

Expected: both windows enter the same match; host typing moves police, client typing moves thief, both screens show the same positions.

- [ ] **Step 6: Manual two-computer test**

On computer A, host and note the displayed LAN IP. On computer B, join that IP.

Expected: same as the two-process test, but over Wi-Fi.

- [ ] **Step 7: Commit**

```bash
git add src/typing_chase/networking.py src/typing_chase/screens.py src/typing_chase/main.py
git commit -m "feat: add lan host join gameplay"
```

## Task 7: Polish MVP Feedback and Docs

**Files:**
- Modify: `src/typing_chase/renderer.py`
- Modify: `README.md`
- Modify: `docs/superpowers/specs/2026-05-16-lan-typing-chase-design.md` only if implementation intentionally differs.

- [ ] **Step 1: Add visible status and error states**

Update renderer helpers so every mode has clear text:

```python
# Menu: "H Host Game" and "J Join Game"
# Host lobby: "Waiting for player..." and host IP/port
# Join screen: current IP text and connection error
# Gameplay: "Penalty" near a player if now < penalty_until
# End: winner and reason plus "Esc to menu"
```

- [ ] **Step 2: Update README with LAN notes**

Add:

```markdown
## LAN Troubleshooting

- Both computers must be on the same Wi-Fi network.
- If joining fails, allow Python through the firewall on the host computer.
- If the host IP does not work, try the IP shown in System Settings > Wi-Fi.
- Use `127.0.0.1` only when testing two windows on the same computer.
```

- [ ] **Step 3: Run tests**

Run: `pytest -q`

Expected: all tests pass.

- [ ] **Step 4: Manual final smoke test**

Run: `python -m typing_chase.main`

Expected: menu is readable, game can be hosted, join screen accepts an IP, and local loopback two-process test still works.

- [ ] **Step 5: Commit**

```bash
git add src/typing_chase/renderer.py README.md docs/superpowers/specs/2026-05-16-lan-typing-chase-design.md
git commit -m "docs: add lan play instructions"
```

## Self-Review

- Spec coverage: the plan covers Python/Pygame, host/join LAN flow, TCP JSON-lines networking, host-authoritative state, typing rules, win conditions, error/status states, README setup, and unit/manual tests.
- Intentional MVP simplification: Task 5 creates a local preview before Task 6 adds real host/join. This gives a visible game earlier while keeping the final target LAN-based.
- Empty-instruction scan: the plan contains no TBD, fill-in instructions, or deferred implementation notes. Task 6 is the largest integration step; it lists exact states, message flow, files, and manual verification.
- Type consistency: `Role.POLICE`, `Role.THIEF`, `Phase`, `GameState`, `TypingProgress`, `JsonLineConnection`, and snapshot keys are consistent across tasks.
