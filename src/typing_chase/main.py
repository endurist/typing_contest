from __future__ import annotations

import pygame

from typing_chase import config
from typing_chase.renderer import Renderer
from typing_chase.screens import MenuScreen


def main() -> None:
    pygame.init()
    screen = pygame.display.set_mode((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
    pygame.display.set_caption("Typing Chase")
    clock = pygame.time.Clock()
    renderer = Renderer(screen)
    screen_state = MenuScreen()

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            else:
                screen_state.handle_event(event)

        if getattr(screen_state, "should_quit", False):
            running = False
            continue

        screen_state.update()
        screen_state.draw(renderer)
        pygame.display.flip()
        screen_state = screen_state.next_screen or screen_state
        clock.tick(config.FPS)

    pygame.quit()


if __name__ == "__main__":
    main()
