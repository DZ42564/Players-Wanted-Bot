import pytest

from game_commands import validate_game_input


def test_rejects_zero_max_players():
    with pytest.raises(ValueError, match="max_players"):
        validate_game_input(0, 2_000_000_000, 1_900_000_000)


def test_rejects_game_in_the_past():
    with pytest.raises(ValueError, match="future"):
        validate_game_input(4, 1_800_000_000, 1_900_000_000)

from game_commands import format_player_status


def test_cancelled_and_closed_status_are_visible():
    assert format_player_status(3, 6, "cancelled").startswith("❌ CANCELLED")
    assert format_player_status(3, 6, "closed").startswith("🔒 CLOSED")
