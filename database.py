import sqlite3
from pathlib import Path
from typing import Any


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row is not None else None


def _column_names(conn: sqlite3.Connection, table: str) -> set[str]:
    return {str(row["name"]) for row in conn.execute(f"PRAGMA table_info({table})")}


def init_db(path: Path) -> None:
    with connect(path) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS games (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                message_id INTEGER,
                creator_user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                image_url TEXT,
                max_players INTEGER NOT NULL CHECK(max_players >= 1),
                start_ts INTEGER NOT NULL,
                reminder_sent INTEGER NOT NULL DEFAULT 0,
                active INTEGER NOT NULL DEFAULT 1,
                status TEXT NOT NULL DEFAULT 'active',
                ping_role_id INTEGER
            );

            CREATE TABLE IF NOT EXISTS signups (
                game_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                signup_ts INTEGER NOT NULL,
                PRIMARY KEY (game_id, user_id),
                FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE
            );
            """
        )
        columns = _column_names(conn, "games")
        if "status" not in columns:
            conn.execute("ALTER TABLE games ADD COLUMN status TEXT NOT NULL DEFAULT 'active'")
        if "ping_role_id" not in columns:
            conn.execute("ALTER TABLE games ADD COLUMN ping_role_id INTEGER")
        # Preserve legacy V1 inactive records as non-active lifecycle records.
        conn.execute(
            "UPDATE games SET status = 'cancelled' WHERE active = 0 AND status = 'active'"
        )


def create_game(
    path: Path,
    guild_id: int,
    channel_id: int,
    creator_user_id: int,
    title: str,
    description: str,
    image_url: str | None,
    max_players: int,
    start_ts: int,
    ping_role_id: int | None = None,
) -> int:
    with connect(path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO games (
                guild_id, channel_id, creator_user_id, title, description,
                image_url, max_players, start_ts, ping_role_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                guild_id,
                channel_id,
                creator_user_id,
                title,
                description,
                image_url,
                max_players,
                start_ts,
                ping_role_id,
            ),
        )
        return int(cursor.lastrowid)


def get_game(path: Path, game_id: int) -> dict[str, Any] | None:
    with connect(path) as conn:
        return _row_to_dict(conn.execute("SELECT * FROM games WHERE id = ?", (game_id,)).fetchone())


def get_game_by_message_id(path: Path, guild_id: int, message_id: int) -> dict[str, Any] | None:
    with connect(path) as conn:
        return _row_to_dict(
            conn.execute(
                "SELECT * FROM games WHERE guild_id = ? AND message_id = ?",
                (guild_id, message_id),
            ).fetchone()
        )


def update_game(path: Path, game_id: int, **fields: Any) -> None:
    allowed = {
        "title", "description", "image_url", "max_players", "start_ts",
        "ping_role_id", "reminder_sent", "channel_id", "message_id",
    }
    unknown = set(fields) - allowed
    if unknown:
        raise ValueError(f"Unsupported game fields: {sorted(unknown)}")
    if not fields:
        return
    assignments = ", ".join(f"{name} = ?" for name in fields)
    values = list(fields.values()) + [game_id]
    with connect(path) as conn:
        conn.execute(f"UPDATE games SET {assignments} WHERE id = ?", values)


def set_game_status(path: Path, game_id: int, status: str) -> None:
    if status not in {"active", "cancelled", "closed"}:
        raise ValueError("invalid game status")
    with connect(path) as conn:
        conn.execute(
            "UPDATE games SET status = ?, active = ? WHERE id = ?",
            (status, 1 if status == "active" else 0, game_id),
        )


def count_signups(path: Path, game_id: int) -> int:
    with connect(path) as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS count FROM signups WHERE game_id = ?", (game_id,)
        ).fetchone()
        return int(row["count"])


def list_signup_user_ids(path: Path, game_id: int) -> list[int]:
    with connect(path) as conn:
        rows = conn.execute(
            "SELECT user_id FROM signups WHERE game_id = ? ORDER BY signup_ts, user_id",
            (game_id,),
        ).fetchall()
        return [int(row["user_id"]) for row in rows]


def try_add_signup(path: Path, game_id: int, user_id: int, now_ts: int) -> str:
    conn = connect(path)
    try:
        conn.execute("BEGIN IMMEDIATE")
        game = conn.execute(
            "SELECT start_ts, max_players, status FROM games WHERE id = ?", (game_id,)
        ).fetchone()
        if game is None or game["status"] != "active":
            conn.rollback()
            return "missing"
        if int(game["start_ts"]) <= now_ts:
            conn.rollback()
            return "started"
        if conn.execute(
            "SELECT 1 FROM signups WHERE game_id = ? AND user_id = ?", (game_id, user_id)
        ).fetchone() is not None:
            conn.rollback()
            return "duplicate"
        count = conn.execute(
            "SELECT COUNT(*) AS count FROM signups WHERE game_id = ?", (game_id,)
        ).fetchone()["count"]
        if int(count) >= int(game["max_players"]):
            conn.rollback()
            return "full"
        conn.execute(
            "INSERT INTO signups (game_id, user_id, signup_ts) VALUES (?, ?, ?)",
            (game_id, user_id, now_ts),
        )
        conn.commit()
        return "added"
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def remove_signup(path: Path, game_id: int, user_id: int) -> str:
    with connect(path) as conn:
        game = conn.execute("SELECT status FROM games WHERE id = ?", (game_id,)).fetchone()
        if game is None or game["status"] != "active":
            return "missing"
        cursor = conn.execute(
            "DELETE FROM signups WHERE game_id = ? AND user_id = ?", (game_id, user_id)
        )
        return "removed" if cursor.rowcount else "not_signed_up"


def set_message_id(path: Path, game_id: int, message_id: int) -> None:
    update_game(path, game_id, message_id=message_id)


def get_games_with_messages(path: Path) -> list[dict[str, Any]]:
    with connect(path) as conn:
        rows = conn.execute(
            "SELECT * FROM games WHERE message_id IS NOT NULL ORDER BY start_ts DESC"
        ).fetchall()
        return [dict(row) for row in rows]


def get_active_future_games(path: Path, now_ts: int) -> list[dict[str, Any]]:
    with connect(path) as conn:
        rows = conn.execute(
            """
            SELECT * FROM games
            WHERE status = 'active' AND start_ts > ? AND message_id IS NOT NULL
            ORDER BY start_ts
            """,
            (now_ts,),
        ).fetchall()
        return [dict(row) for row in rows]


def close_past_games(path: Path, now_ts: int) -> list[int]:
    with connect(path) as conn:
        rows = conn.execute(
            "SELECT id FROM games WHERE status = 'active' AND start_ts <= ?",
            (now_ts,),
        ).fetchall()
        ids = [int(row["id"]) for row in rows]
        if ids:
            conn.executemany(
                "UPDATE games SET status = 'closed', active = 0 WHERE id = ?",
                [(game_id,) for game_id in ids],
            )
        return ids


def get_games_due_for_reminder(path: Path, now_ts: int, reminder_hours: int) -> list[dict[str, Any]]:
    cutoff = now_ts + reminder_hours * 3600
    with connect(path) as conn:
        rows = conn.execute(
            """
            SELECT * FROM games
            WHERE status = 'active'
              AND reminder_sent = 0
              AND start_ts > ?
              AND start_ts <= ?
            ORDER BY start_ts
            """,
            (now_ts, cutoff),
        ).fetchall()
        return [dict(row) for row in rows]


def mark_reminder_sent(path: Path, game_id: int) -> None:
    update_game(path, game_id, reminder_sent=1)
