from __future__ import annotations

import time

import pygame

from typing_chase.game_state import GameState, Role


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
