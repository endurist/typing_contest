# LAN Typing Chase Design

## Goal

Build a first playable Python game where two players on two computers in the same Wi-Fi network compete in a 2D typing chase. One player is the police officer, the other is the thief. Each player uses their own full keyboard on their own computer.

The first version should be simple, reliable, and fun enough to test the core idea:

- Typing correctly moves your character forward.
- Mistakes slow you down.
- The police officer wins by catching the thief.
- The thief wins by reaching the escape line before being caught.

This version does not include public internet play, accounts, matchmaking, custom maps, power-ups, or advanced anti-cheat.

## User Experience

Both computers run the same Python program.

At launch, the player chooses one of two modes:

- **Host Game**: starts a local server and displays the host computer's LAN IP address and port.
- **Join Game**: asks for the host IP address and connects to the host.

After the client joins:

- The host becomes the police officer by default.
- The joining player becomes the thief by default.
- The game shows a ready screen.
- When both players are ready, the match starts after a short countdown.

During the match, both screens show:

- A horizontal 2D street map.
- The police officer and thief positions.
- A timer.
- Each player's typing prompt and progress.
- Current winner/status text.

The first version can use simple geometric art: colored circles or small rectangles for characters, a road lane for the map, and clean text UI.

## Core Gameplay

The first map is a single horizontal chase lane.

The thief starts ahead of the police officer. Both players move toward the right side of the screen:

- Police starts at position `0`.
- Thief starts at position `START_GAP`, such as `180` pixels.
- Escape line is at `TRACK_LENGTH`, such as `1000` pixels.

Each player receives a typing prompt. The prompts can be the same sentence or separate sentences from the same word bank. For the first implementation, both players can use the same current prompt so the race feels fair.

Typing rules:

- Correct next character advances that player's prompt cursor.
- Every correct character adds movement progress.
- Completing a prompt loads the next prompt.
- Wrong character applies a short penalty, such as `0.35` seconds where correct input is ignored or movement is paused.
- Backspace is ignored in the MVP.
- Case is normalized to lowercase.

Win conditions:

- Police wins if `police_position + CATCH_DISTANCE >= thief_position`.
- Thief wins if `thief_position >= TRACK_LENGTH`.
- If the 90-second round timer reaches zero before either condition happens, the thief wins by escape timeout.

Recommended first tuning:

- `START_GAP = 180`
- `TRACK_LENGTH = 1000`
- `CATCH_DISTANCE = 28`
- `MOVE_PER_CHAR = 8`
- `MISTAKE_PENALTY_SECONDS = 0.35`
- `ROUND_SECONDS = 90`

These values should live in a single configuration module so they are easy to adjust after playtesting.

## Technical Approach

Use **Python + Pygame + TCP sockets**.

Pygame handles:

- Window creation.
- Keyboard events.
- Drawing the road, characters, text, menus, and result screen.
- Frame timing.

TCP sockets handle LAN communication:

- The host opens a TCP server on a fixed port, such as `5050`.
- The client connects by entering the host IP address.
- The client sends input events to the host.
- The host owns authoritative game state.
- The host broadcasts snapshots to the client.

The host-authoritative model keeps the first version simpler:

- Only one machine decides positions and win conditions.
- The client cannot accidentally diverge into a different game state.
- Debugging is easier than peer-to-peer sync.

## Networking Protocol

Messages are newline-delimited JSON objects over TCP.

Client to host:

```json
{"type": "join", "name": "Player 2"}
{"type": "ready"}
{"type": "key", "key": "a", "time": 1778900000.0}
```

Host to client:

```json
{"type": "welcome", "player_id": "thief"}
{"type": "state", "game": {...}}
{"type": "match_end", "winner": "police", "reason": "caught"}
```

Both sides can send:

```json
{"type": "ping", "time": 1778900000.0}
{"type": "error", "message": "Connection lost"}
```

MVP state snapshots should include:

- Match phase: `lobby`, `countdown`, `playing`, `ended`.
- Role assignment.
- Police position.
- Thief position.
- Timer remaining.
- Current prompt text.
- Per-player prompt cursor.
- Per-player penalty remaining.
- Winner and reason when ended.

The host should broadcast snapshots at a fixed rate, such as 20 times per second. Input events are small and can be sent immediately.

## Program Structure

Recommended source layout:

```text
typing_contest/
  pyproject.toml
  README.md
  src/
    typing_chase/
      __init__.py
      main.py
      config.py
      game_state.py
      typing_logic.py
      networking.py
      screens.py
      renderer.py
      assets.py
  tests/
    test_typing_logic.py
    test_game_state.py
```

Module responsibilities:

- `main.py`: app entry point and top-level Pygame loop.
- `config.py`: gameplay constants, screen size, network port.
- `game_state.py`: pure game rules, positions, phase transitions, win checks.
- `typing_logic.py`: prompt cursor, correct key handling, wrong-key penalty.
- `networking.py`: host/client TCP connection, JSON message framing, queues.
- `screens.py`: menu, lobby, countdown, gameplay, result screen flow.
- `renderer.py`: draw map, characters, UI text, prompt progress.
- `assets.py`: font loading and optional simple color definitions.

Game logic should be testable without Pygame or sockets. Pygame and network code should call into pure rule objects instead of embedding all behavior in the render loop.

## Error Handling

The MVP should handle common local-network failures gracefully:

- If the client cannot connect, show a readable error and return to the join screen.
- If either side disconnects mid-game, show "Connection lost" and return to menu.
- If the host port is already in use, show an error and ask the user to try another port or close the existing game.
- If the user enters an invalid IP, stay on the join screen and show a short message.

The MVP does not need automatic reconnection.

## Visual Design

The first version should be readable and direct, not decorative.

Recommended style:

- 960x540 window.
- Horizontal road across the center.
- Police in blue.
- Thief in dark gray or black.
- Escape line on the right.
- Player typing panels at the bottom.
- Timer and role labels at the top.

Text must be large enough to read during fast typing. The current character can be highlighted so each player knows exactly where they are in the prompt.

## Testing Strategy

Unit tests:

- Correct character advances prompt cursor.
- Wrong character applies penalty.
- Penalty blocks or delays progress as designed.
- Completing a prompt loads the next prompt.
- Police catch condition works.
- Thief escape condition works.
- Timer win condition awards the thief a timeout win.

Manual tests:

- Host game starts and displays LAN IP.
- Client can join by IP on the same Wi-Fi network.
- Both players can type and see positions update.
- Wrong-key penalty is visible.
- Police can win by catching the thief.
- Thief can win by reaching the escape line.
- Disconnecting one side shows an error instead of crashing.

## MVP Boundaries

Included in the first version:

- Two-computer LAN play.
- Host/join menu.
- One horizontal chase map.
- Police and thief roles.
- Full keyboard typing on both machines.
- Host-authoritative game state.
- Fixed MVP role assignment: host is police, client is thief.
- 90-second round timer.
- Simple Pygame rendering.
- Basic unit tests for rules.

Excluded from the first version:

- Internet multiplayer outside the same Wi-Fi.
- Matchmaking, accounts, lobby browser, or chat.
- Multiple maps.
- Items, powers, obstacles, or maze navigation.
- Custom prompt editor.
- Role selection or role swapping.
- Polished sprites or animations.
- Sound effects and music.

## Open Decisions

The current design chooses English lowercase prompts for the MVP because they are easier to process consistently across keyboards and operating systems. Chinese prompts can be added later, but they require IME handling and would make the first implementation more fragile.

The current design chooses TCP instead of UDP because correctness and simplicity matter more than ultra-low latency for the first version.
