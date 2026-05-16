from typing_chase.game_state import GameState, Phase, Role


def test_initial_state_places_thief_ahead():
    state = GameState.new_match()

    assert state.police.position == 0.0
    assert state.thief.position == 180.0
    assert state.phase == Phase.LOBBY


def test_start_sets_playing_phase_and_start_time():
    state = GameState.new_match()

    state.start(now=10.0)

    assert state.phase == Phase.PLAYING
    assert state.started_at == 10.0


def test_police_moves_on_correct_key():
    state = GameState.new_match()
    state.start(now=0.0)

    state.apply_key(Role.POLICE, "t", now=0.0)

    assert state.police.position == 8.0
    assert state.thief.position == 180.0


def test_invalid_role_does_not_move_either_player():
    state = GameState.new_match()
    state.start(now=0.0)

    state.apply_key("dispatcher", "t", now=0.0)

    assert state.police.position == 0.0
    assert state.thief.position == 180.0


def test_police_wins_when_close_enough():
    state = GameState.new_match()
    state.start(now=0.0)
    state.police.position = 160.0
    state.thief.position = 188.0

    state.update(now=1.0)

    assert state.phase == Phase.ENDED
    assert state.winner == Role.POLICE
    assert state.end_reason == "caught"


def test_thief_wins_at_escape_line():
    state = GameState.new_match()
    state.start(now=0.0)
    state.thief.position = 1000.0

    state.update(now=1.0)

    assert state.phase == Phase.ENDED
    assert state.winner == Role.THIEF
    assert state.end_reason == "escaped"


def test_thief_wins_when_timer_expires():
    state = GameState.new_match()
    state.start(now=10.0)

    state.update(now=100.0)

    assert state.phase == Phase.ENDED
    assert state.winner == Role.THIEF
    assert state.end_reason == "timeout"


def test_snapshot_round_trips_basic_state():
    state = GameState.new_match()
    state.start(now=0.0)
    state.police.position = 12.0

    snapshot = state.to_snapshot()

    assert snapshot["phase"] == "playing"
    assert snapshot["police"]["position"] == 12.0
    assert snapshot["thief"]["position"] == 180.0


def test_snapshot_without_now_does_not_exceed_round_seconds_after_start():
    state = GameState.new_match()
    state.start(now=10.0)

    snapshot = state.to_snapshot()

    assert snapshot["timer_remaining"] == 90.0
