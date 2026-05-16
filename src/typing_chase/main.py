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
