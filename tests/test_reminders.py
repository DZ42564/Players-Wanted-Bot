from unittest.mock import AsyncMock, MagicMock

import pytest

import reminders


class FakeUser:
    def __init__(self, fail=False):
        self.fail = fail
        self.send = AsyncMock(side_effect=RuntimeError("blocked") if fail else None)


@pytest.mark.asyncio
async def test_dm_failure_does_not_stop_later_users(monkeypatch, tmp_path):
    users = {1: FakeUser(fail=True), 2: FakeUser(fail=False)}
    bot = AsyncMock()
    bot.get_guild = MagicMock(return_value=None)
    bot.fetch_user.side_effect = lambda user_id: users[user_id]

    monkeypatch.setattr(reminders.database, "get_games_due_for_reminder", lambda *args: [{
        "id": 5,
        "title": "Test Game",
        "start_ts": 2_000_000_000,
        "guild_id": 1,
        "channel_id": 10,
        "message_id": 20,
    }])
    monkeypatch.setattr(reminders.database, "list_signup_user_ids", lambda *args: [1, 2])
    mark = AsyncMock()
    monkeypatch.setattr(reminders, "mark_sent", mark)

    await reminders.send_due_reminders(bot, tmp_path / "games.db", 1_999_970_000)

    assert users[1].send.await_count == 1
    assert users[2].send.await_count == 1
    mark.assert_awaited_once_with(tmp_path / "games.db", 5)


def test_reminder_text_includes_server_name_and_jump_link():
    game = {
        "id": 1,
        "title": "Test Game",
        "start_ts": 2_000_000_000,
        "guild_id": 10,
        "channel_id": 20,
        "message_id": 30,
    }
    text = reminders.build_reminder_text(game, server_name="The Forge")
    assert "The Forge" in text
    assert "https://discord.com/channels/10/20/30" in text


def test_cancellation_text_is_clear():
    game = {"title": "Cancelled Game", "start_ts": 2_000_000_000}
    text = reminders.build_cancellation_text(game)
    assert "cancelled" in text.lower()
    assert "Cancelled Game" in text
