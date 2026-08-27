from unittest.mock import MagicMock

import pytest

import game_views


@pytest.mark.asyncio
async def test_restore_views_registers_each_future_game(monkeypatch, tmp_path):
    monkeypatch.setattr(
        game_views.database,
        "get_games_with_messages",
        lambda path: [{"id": 10}, {"id": 11}],
    )
    monkeypatch.setattr(game_views.GameSignupView, "_apply_state", lambda self: None)
    bot = MagicMock()

    await game_views.restore_views(bot, tmp_path / "games.db", 123)

    assert bot.add_view.call_count == 2


def test_view_has_view_players_button(tmp_path):
    path = tmp_path / "games.db"
    game_views.database.init_db(path)
    game_id = game_views.database.create_game(path, 1, 2, 3, "Test", "Desc", None, 2, 2_000_000_000)
    view = game_views.GameSignupView(game_id, path)
    labels = [child.label for child in view.children]
    assert labels == ["Sign Up", "Withdraw", "View Players"]
