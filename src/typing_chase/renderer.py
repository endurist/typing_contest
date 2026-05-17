from __future__ import annotations

import pygame

from typing_chase import config

BLUE = (35, 95, 191)
DARK = (34, 34, 34)
ROAD = (217, 222, 231)
TEXT = (31, 47, 67)
WHITE = (250, 252, 255)


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
            self.centered(f"{snapshot['winner']} wins: {snapshot['end_reason']}", 82)
            self.text("R - Next round", (390, 102))

    def _track_to_screen(self, position: float) -> int:
        return int(60 + min(position / config.TRACK_LENGTH, 1.0) * 800)

    def _draw_prompt_panel(self, label: str, player: dict, y: int) -> None:
        rect = pygame.Rect(60, y, 840, 68)
        pygame.draw.rect(self.screen, WHITE, rect)
        pygame.draw.rect(self.screen, (151, 175, 208), rect, 2)
        prompt = player["prompt"]
        cursor = player["cursor"]
        label_text = f"{label} {cursor}/{len(prompt)}: "
        typed_text, remaining_text = self._visible_prompt(prompt, cursor)
        text_y = y + 12

        self.text(label_text, (76, text_y), TEXT)
        typed_x = 76 + self.font.size(label_text)[0]
        self.text(typed_text, (typed_x, text_y), BLUE)
        remaining_x = typed_x + self.font.size(typed_text)[0]
        self.text(remaining_text, (remaining_x, text_y), TEXT)

    @staticmethod
    def _visible_prompt(prompt: str, cursor: int) -> tuple[str, str]:
        typed_start = max(0, cursor - 24)
        typed_text = prompt[typed_start:cursor]
        remaining_end = min(len(prompt), cursor + 48)
        remaining_text = prompt[cursor:remaining_end]

        if typed_start > 0:
            typed_text = "..." + typed_text
        if remaining_end < len(prompt):
            remaining_text = remaining_text + "..."

        return typed_text, remaining_text
