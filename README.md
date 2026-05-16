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

## LAN Play

1. Connect both computers to the same Wi-Fi network.
2. On computer A, run the game and press `H` to host.
3. On computer B, run the game, press `J`, enter the host IP shown on computer A, and press Enter.
4. When the client is connected, the host presses Space to start.
5. The host plays police. The joining player plays thief.

## LAN Troubleshooting

- Both computers must be on the same Wi-Fi network.
- If joining fails, allow Python through the firewall on the host computer.
- If the host IP shown in game does not work, try the IP shown in System Settings > Wi-Fi.
- Use `127.0.0.1` only when testing two windows on the same computer.
- If hosting fails, another copy of the game may already be using port `5050`.

## Test

```bash
pytest
```
