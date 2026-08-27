from pathlib import Path

import database


def make_db(tmp_path: Path) -> Path:
    path = tmp_path / "games.db"
    database.init_db(path)
    return path


def create_future_game(path: Path, max_players: int = 2) -> int:
    return database.create_game(
        path=path,
        guild_id=1,
        channel_id=2,
        creator_user_id=3,
        title="Test Game",
        description="Desc",
        image_url=None,
        max_players=max_players,
        start_ts=2_000_000_000,
    )


def test_duplicate_signup_is_rejected(tmp_path):
    path = make_db(tmp_path)
    game_id = create_future_game(path)

    assert database.try_add_signup(path, game_id, 100, 1_900_000_000) == "added"
    assert database.try_add_signup(path, game_id, 100, 1_900_000_001) == "duplicate"
    assert database.count_signups(path, game_id) == 1


def test_signup_never_exceeds_capacity(tmp_path):
    path = make_db(tmp_path)
    game_id = create_future_game(path, max_players=1)

    assert database.try_add_signup(path, game_id, 100, 1_900_000_000) == "added"
    assert database.try_add_signup(path, game_id, 101, 1_900_000_000) == "full"
    assert database.count_signups(path, game_id) == 1


def test_withdrawal_reopens_full_game(tmp_path):
    path = make_db(tmp_path)
    game_id = create_future_game(path, max_players=1)

    assert database.try_add_signup(path, game_id, 100, 1_900_000_000) == "added"
    assert database.remove_signup(path, game_id, 100) == "removed"
    assert database.try_add_signup(path, game_id, 101, 1_900_000_010) == "added"


def test_v1_database_migrates_without_losing_game(tmp_path):
    path = tmp_path / "legacy.db"
    with database.connect(path) as conn:
        conn.executescript("""
        CREATE TABLE games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
            channel_id INTEGER NOT NULL,
            message_id INTEGER,
            creator_user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            image_url TEXT,
            max_players INTEGER NOT NULL,
            start_ts INTEGER NOT NULL,
            reminder_sent INTEGER NOT NULL DEFAULT 0,
            active INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE signups (
            game_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            signup_ts INTEGER NOT NULL,
            PRIMARY KEY (game_id, user_id)
        );
        INSERT INTO games (guild_id, channel_id, message_id, creator_user_id, title, description, max_players, start_ts)
        VALUES (1, 2, 99, 3, 'Legacy', 'Still here', 5, 2000000000);
        """)
    database.init_db(path)
    game = database.get_game(path, 1)
    assert game["title"] == "Legacy"
    assert game["status"] == "active"
    assert game["ping_role_id"] is None


def test_game_can_be_found_and_updated_by_message_id(tmp_path):
    path = make_db(tmp_path)
    game_id = create_future_game(path)
    database.set_message_id(path, game_id, 555)
    game = database.get_game_by_message_id(path, 1, 555)
    assert game["id"] == game_id
    database.update_game(path, game_id, title="Changed", max_players=7, ping_role_id=42)
    changed = database.get_game(path, game_id)
    assert changed["title"] == "Changed"
    assert changed["max_players"] == 7
    assert changed["ping_role_id"] == 42


def test_cancelled_game_rejects_signup_and_withdrawal(tmp_path):
    path = make_db(tmp_path)
    game_id = create_future_game(path)
    assert database.try_add_signup(path, game_id, 100, 1_900_000_000) == "added"
    database.set_game_status(path, game_id, "cancelled")
    assert database.try_add_signup(path, game_id, 101, 1_900_000_001) == "missing"
    assert database.remove_signup(path, game_id, 100) == "missing"


def test_close_past_games_marks_active_games_closed(tmp_path):
    path = make_db(tmp_path)
    game_id = create_future_game(path)
    assert database.close_past_games(path, 2_000_000_001) == [game_id]
    assert database.get_game(path, game_id)["status"] == "closed"
