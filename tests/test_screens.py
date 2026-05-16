import pygame

from typing_chase.screens import LocalPreviewGame


def test_local_preview_starts_as_police_and_moves_on_key():
    game = LocalPreviewGame()
    start_position = game.state.police.position
    first_prompt_character = game.state.police.typing.prompt[0]

    event = pygame.event.Event(pygame.KEYDOWN, unicode=first_prompt_character)
    game.handle_event(event)

    assert game.local_role.value == "police"
    assert game.state.police.position > start_position
    assert game.snapshot()["phase"] == "playing"
