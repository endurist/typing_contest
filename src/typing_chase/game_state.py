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
    prompt_index: int = 0
    started_at: float | None = None
    winner: Role | None = None
    end_reason: str | None = None

    @classmethod
    def new_match(cls, prompt_index: int = 0) -> "GameState":
        normalized_prompt_index = prompt_index % len(config.PROMPTS)
        prompt = config.PROMPTS[normalized_prompt_index]
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
            prompt_index=normalized_prompt_index,
        )

    def start(self, now: float) -> None:
        self.phase = Phase.PLAYING
        self.started_at = now

    def apply_key(self, role: Role, key: str, now: float) -> None:
        if self.phase != Phase.PLAYING or len(key) != 1:
            return

        if role == Role.POLICE:
            player = self.police
        elif role == Role.THIEF:
            player = self.thief
        else:
            return

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
        return min(config.ROUND_SECONDS, max(0.0, config.ROUND_SECONDS - (now - self.started_at)))

    def to_snapshot(self, now: float | None = None) -> dict:
        current_time = 0.0 if now is None else now
        return {
            "phase": self.phase.value,
            "timer_remaining": self.timer_remaining(current_time),
            "winner": None if self.winner is None else self.winner.value,
            "end_reason": self.end_reason,
            "prompt_index": self.prompt_index,
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
