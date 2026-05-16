from typing_chase.typing_logic import TypingProgress


def test_correct_character_advances_cursor_and_position_delta():
    progress = TypingProgress(prompt="abc", move_per_char=8.0, mistake_penalty_seconds=0.35)

    result = progress.handle_key("a", now=0.0)

    assert result.correct is True
    assert result.move_delta == 8.0
    assert progress.cursor == 1
    assert progress.penalty_until == 0.0


def test_wrong_character_sets_penalty_and_does_not_advance():
    progress = TypingProgress(prompt="abc", move_per_char=8.0, mistake_penalty_seconds=0.35)

    result = progress.handle_key("z", now=1.0)

    assert result.correct is False
    assert result.move_delta == 0.0
    assert progress.cursor == 0
    assert progress.penalty_until == 1.35


def test_input_during_penalty_is_ignored():
    progress = TypingProgress(prompt="abc", move_per_char=8.0, mistake_penalty_seconds=0.35)
    progress.handle_key("z", now=1.0)

    result = progress.handle_key("a", now=1.1)

    assert result.correct is False
    assert result.ignored is True
    assert result.move_delta == 0.0
    assert progress.cursor == 0


def test_completing_prompt_wraps_to_next_prompt():
    progress = TypingProgress(prompt="ab", move_per_char=8.0, mistake_penalty_seconds=0.35)

    progress.handle_key("a", now=0.0)
    result = progress.handle_key("b", now=0.1)

    assert result.completed_prompt is True
    assert progress.cursor == 0
