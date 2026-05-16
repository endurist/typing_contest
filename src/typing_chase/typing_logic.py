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
