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
