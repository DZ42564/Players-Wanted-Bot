# Discord Game Signup Bot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a simple Discord bot that creates game signup posts, enforces player limits, supports self-withdrawal, survives restarts, and DMs registered players 8 hours before game time.

**Architecture:** A single Python 3.12+ process uses `discord.py` for Discord interactions and the standard-library `sqlite3` module for persistence. Game creation, database access, interactive views, and reminders live in separate focused modules, while `bot.py` wires them together and restores persistent views on startup.

**Tech Stack:** Python 3.12+, discord.py 2.x, SQLite (`sqlite3`), python-dotenv, zoneinfo, pytest, pytest-asyncio

**Spec:** `docs/superpowers/specs/2026-08-26-discord-game-signup-bot-design.md`

## Global Constraints

- Python 3.12+.
- Use `discord.py` 2.x.
- Use one SQLite database file at `data/games.db`.
- Use `python-dotenv` for the bot token and simple configuration.
- Interpret creator-entered date/time values in `America/New_York`.
- Store game start times as UTC Unix timestamps.
- Public posts show only `Players: X / Max`; no player names in V1.
- Reminder delivery is DM-only, exactly once per game, beginning when the game is within 8 hours.
- Reminder checks run every 5 minutes.
- Persistent buttons must be restored after bot restarts.
- Deferred features remain out of scope: View Players, waitlist, setup wizard, edit/cancel commands, multiple creator timezones, web dashboard, external database.

---

## File Map

- `bot.py` — bot startup, command registration, persistent-view restoration, reminder startup.
- `config.py` — environment loading and constants.
- `database.py` — schema initialization and all game/signup persistence operations.
- `game_commands.py` — `/create-game`, validation, time parsing, initial embed/post creation.
- `game_views.py` — Sign Up / Withdraw buttons, per-game locks, refreshed embed state.
- `reminders.py` — reminder selection and DM delivery.
- `tests/test_database.py` — signup limits, duplicate rejection, withdrawal behavior.
- `tests/test_time_parsing.py` — Eastern Time and DST conversion.
- `tests/test_reminders.py` — once-only reminders and DM failure isolation.
- `tests/test_views.py` — persistent view restoration data flow.
- `requirements.txt` — runtime/test dependencies.
- `.env.example` — token/config template.
- `README.md` — exact beginner-friendly setup and run instructions.
- `data/.gitkeep` — keeps the data directory in git without committing the live database.

---

### Task 1: Project Bootstrap and Configuration

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `config.py`
- Create: `data/.gitkeep`
- Create: `tests/test_config.py`

**Interfaces:**
- Produces: `config.BOT_TOKEN: str`, `config.DATABASE_PATH: pathlib.Path`, `config.EASTERN_TZ: zoneinfo.ZoneInfo`, `config.REMINDER_HOURS: int`, `config.REMINDER_POLL_SECONDS: int`

- [ ] **Step 1: Write the failing configuration test**

```python
# tests/test_config.py
from pathlib import Path

import config


def test_config_constants():
    assert config.DATABASE_PATH == Path("data/games.db")
    assert config.EASTERN_TZ.key == "America/New_York"
    assert config.REMINDER_HOURS == 8
    assert config.REMINDER_POLL_SECONDS == 300
```

- [ ] **Step 2: Run the test and confirm it fails**

Run:

```bash
pytest tests/test_config.py -v
```

Expected: FAIL because `config.py` does not exist yet.

- [ ] **Step 3: Add dependencies and minimal configuration**

```text
# requirements.txt
discord.py>=2.4,<3
python-dotenv>=1.0,<2
pytest>=8,<9
pytest-asyncio>=0.24,<1
```

```text
# .env.example
DISCORD_BOT_TOKEN=replace_me
```

```python
# config.py
import os
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")
DATABASE_PATH = Path("data/games.db")
EASTERN_TZ = ZoneInfo("America/New_York")
REMINDER_HOURS = 8
REMINDER_POLL_SECONDS = 300
```

- [ ] **Step 4: Run the test and confirm it passes**

```bash
pytest tests/test_config.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add requirements.txt .env.example config.py data/.gitkeep tests/test_config.py
git commit -m "chore: bootstrap discord bot project"
```

---

### Task 2: Database Schema and Signup Rules

**Files:**
- Create: `database.py`
- Create: `tests/test_database.py`

**Interfaces:**
- Produces: `init_db(path: Path) -> None`
- Produces: `create_game(...) -> int`
- Produces: `get_game(game_id: int) -> dict | None`
- Produces: `count_signups(game_id: int) -> int`
- Produces: `list_signup_user_ids(game_id: int) -> list[int]`
- Produces: `try_add_signup(game_id: int, user_id: int, now_ts: int) -> str`
- Produces: `remove_signup(game_id: int, user_id: int) -> str`
- Produces: `set_message_id(game_id: int, message_id: int) -> None`
- Produces: `get_active_future_games(now_ts: int) -> list[dict]`

Return values for signup methods are stable strings: `added`, `duplicate`, `full`, `started`, `removed`, `not_signed_up`, `missing`.

- [ ] **Step 1: Write failing tests for duplicate signup, capacity, and withdrawal**

```python
# tests/test_database.py
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
```

- [ ] **Step 2: Run tests and confirm failure**

```bash
pytest tests/test_database.py -v
```

Expected: FAIL because `database.py` does not exist.

- [ ] **Step 3: Implement schema and database operations**

Use SQLite with foreign keys enabled and an immediate transaction in `try_add_signup` so capacity is checked and signup is inserted atomically.

```python
# database.py
import sqlite3
from pathlib import Path


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(path: Path) -> None:
    with connect(path) as conn:
        conn.executescript("""
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
            active INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS signups (
            game_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            signup_ts INTEGER NOT NULL,
            PRIMARY KEY (game_id, user_id),
            FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE
        );
        """)
```

Complete the remaining functions using parameterized SQL only. `try_add_signup` must run `BEGIN IMMEDIATE`, fetch `start_ts` and `max_players`, reject started/full/duplicate cases, insert once, then commit.

- [ ] **Step 4: Run database tests**

```bash
pytest tests/test_database.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add database.py tests/test_database.py
git commit -m "feat: add persistent game signup database"
```

---

### Task 3: Eastern-Time Parsing and Embed Helpers

**Files:**
- Create: `game_commands.py`
- Create: `tests/test_time_parsing.py`

**Interfaces:**
- Consumes: `config.EASTERN_TZ`
- Produces: `parse_eastern_datetime(date_text: str, time_text: str) -> int`
- Produces: `build_game_embed(game: dict, signup_count: int) -> discord.Embed`
- Produces: `format_player_status(signup_count: int, max_players: int) -> str`

- [ ] **Step 1: Write failing timezone tests**

```python
# tests/test_time_parsing.py
from datetime import datetime, timezone

from game_commands import parse_eastern_datetime


def test_winter_eastern_time_converts_to_utc():
    ts = parse_eastern_datetime("2026-01-15", "19:00")
    assert datetime.fromtimestamp(ts, timezone.utc).isoformat() == "2026-01-16T00:00:00+00:00"


def test_summer_eastern_time_converts_to_utc_with_dst():
    ts = parse_eastern_datetime("2026-08-15", "19:00")
    assert datetime.fromtimestamp(ts, timezone.utc).isoformat() == "2026-08-15T23:00:00+00:00"
```

- [ ] **Step 2: Run tests and confirm failure**

```bash
pytest tests/test_time_parsing.py -v
```

Expected: FAIL because `game_commands.py` does not exist.

- [ ] **Step 3: Implement time parsing and display helpers**

```python
# game_commands.py
from datetime import datetime, timezone

import discord

from config import EASTERN_TZ


def parse_eastern_datetime(date_text: str, time_text: str) -> int:
    naive = datetime.strptime(f"{date_text} {time_text}", "%Y-%m-%d %H:%M")
    eastern = naive.replace(tzinfo=EASTERN_TZ)
    return int(eastern.astimezone(timezone.utc).timestamp())


def format_player_status(signup_count: int, max_players: int) -> str:
    if signup_count >= max_players:
        return f"🔴 FULL — Players: {signup_count} / {max_players}"
    return f"Players: {signup_count} / {max_players}"


def build_game_embed(game: dict, signup_count: int) -> discord.Embed:
    embed = discord.Embed(title=game["title"], description=game["description"])
    embed.add_field(
        name="📅 Game Time",
        value=f"<t:{game['start_ts']}:F>\n<t:{game['start_ts']}:R>",
        inline=False,
    )
    embed.add_field(
        name="👥 Players",
        value=format_player_status(signup_count, game["max_players"]),
        inline=False,
    )
    if game.get("image_url"):
        embed.set_image(url=game["image_url"])
    return embed
```

- [ ] **Step 4: Run timezone tests**

```bash
pytest tests/test_time_parsing.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add game_commands.py tests/test_time_parsing.py
git commit -m "feat: parse eastern game times and build embeds"
```

---

### Task 4: Persistent Signup and Withdraw Buttons

**Files:**
- Create: `game_views.py`
- Create: `tests/test_views.py`

**Interfaces:**
- Consumes: `database.get_game`, `database.count_signups`, `database.try_add_signup`, `database.remove_signup`
- Consumes: `game_commands.build_game_embed`
- Produces: `GameSignupView(game_id: int, db_path: Path)`
- Produces: `restore_views(bot: discord.Client, db_path: Path, now_ts: int) -> None`

- [ ] **Step 1: Write a failing restoration test around active future games**

```python
# tests/test_views.py
from unittest.mock import MagicMock

import pytest

import game_views


@pytest.mark.asyncio
async def test_restore_views_registers_each_future_game(monkeypatch, tmp_path):
    monkeypatch.setattr(
        game_views.database,
        "get_active_future_games",
        lambda path, now_ts: [{"id": 10}, {"id": 11}],
    )
    bot = MagicMock()

    await game_views.restore_views(bot, tmp_path / "games.db", 123)

    assert bot.add_view.call_count == 2
```

- [ ] **Step 2: Run the test and confirm failure**

```bash
pytest tests/test_views.py -v
```

Expected: FAIL because `game_views.py` does not exist.

- [ ] **Step 3: Implement the persistent view and per-game lock**

`GameSignupView` uses `timeout=None` and stable custom IDs:

```python
signup_custom_id = f"game:{game_id}:signup"
withdraw_custom_id = f"game:{game_id}:withdraw"
```

Maintain module-level locks:

```python
_game_locks: dict[int, asyncio.Lock] = {}


def get_game_lock(game_id: int) -> asyncio.Lock:
    return _game_locks.setdefault(game_id, asyncio.Lock())
```

On Sign Up:
1. Acquire the game lock.
2. Call `try_add_signup` with current UTC timestamp.
3. Send an ephemeral message matching the result.
4. On success, refresh the original message embed and disabled state.

On Withdraw:
1. Acquire the same lock.
2. Call `remove_signup`.
3. Send ephemeral success/error text.
4. On success, refresh the embed and Sign Up button state.

`restore_views` loops active future games and calls:

```python
bot.add_view(GameSignupView(game["id"], db_path))
```

- [ ] **Step 4: Run the restoration test**

```bash
pytest tests/test_views.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add game_views.py tests/test_views.py
git commit -m "feat: add persistent signup and withdraw buttons"
```

---

### Task 5: `/create-game` Slash Command

**Files:**
- Modify: `game_commands.py`
- Create: `tests/test_create_game.py`

**Interfaces:**
- Consumes: `database.create_game`, `database.set_message_id`, `GameSignupView`, `parse_eastern_datetime`, `build_game_embed`
- Produces: `register_game_commands(tree: discord.app_commands.CommandTree, db_path: Path) -> None`

- [ ] **Step 1: Write failing validation tests**

```python
# tests/test_create_game.py
import pytest

from game_commands import validate_game_input


def test_rejects_zero_max_players():
    with pytest.raises(ValueError, match="max_players"):
        validate_game_input(0, 2_000_000_000, 1_900_000_000)


def test_rejects_game_in_the_past():
    with pytest.raises(ValueError, match="future"):
        validate_game_input(4, 1_800_000_000, 1_900_000_000)
```

- [ ] **Step 2: Run tests and confirm failure**

```bash
pytest tests/test_create_game.py -v
```

Expected: FAIL because `validate_game_input` does not exist.

- [ ] **Step 3: Implement validation and slash-command registration**

Add:

```python
def validate_game_input(max_players: int, start_ts: int, now_ts: int) -> None:
    if max_players < 1:
        raise ValueError("max_players must be at least 1")
    if start_ts <= now_ts:
        raise ValueError("game time must be in the future")
```

Register `/create-game` with arguments:
- `title: str`
- `max_players: int`
- `description: str`
- `date: str`
- `time: str`
- `image: discord.Attachment | None`

Command flow:
1. `await interaction.response.defer(ephemeral=True)`.
2. Parse Eastern date/time; on `ValueError`, send `I couldn't create that game. Check the date and time and try again.`
3. Validate max players and future time.
4. Save the game with `image.url if image else None`.
5. Build initial embed with zero signups.
6. Send the public message to `interaction.channel` with `GameSignupView`.
7. Save the returned message ID.
8. Send ephemeral confirmation to creator.

- [ ] **Step 4: Run validation tests**

```bash
pytest tests/test_create_game.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add game_commands.py tests/test_create_game.py
git commit -m "feat: add create-game slash command"
```

---

### Task 6: Reminder Selection and DM Delivery

**Files:**
- Create: `reminders.py`
- Create: `tests/test_reminders.py`
- Modify: `database.py`

**Interfaces:**
- Adds: `get_games_due_for_reminder(path: Path, now_ts: int, reminder_hours: int) -> list[dict]`
- Adds: `mark_reminder_sent(path: Path, game_id: int) -> None`
- Produces: `send_due_reminders(bot: discord.Client, db_path: Path, now_ts: int) -> None`
- Produces: `start_reminder_loop(bot: discord.Client, db_path: Path) -> tasks.Loop`

- [ ] **Step 1: Write failing reminder tests**

```python
# tests/test_reminders.py
from unittest.mock import AsyncMock

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
    bot.fetch_user.side_effect = lambda user_id: users[user_id]

    monkeypatch.setattr(reminders.database, "get_games_due_for_reminder", lambda *args: [{
        "id": 5,
        "title": "Test Game",
        "start_ts": 2_000_000_000,
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
```

- [ ] **Step 2: Run tests and confirm failure**

```bash
pytest tests/test_reminders.py -v
```

Expected: FAIL because `reminders.py` does not exist.

- [ ] **Step 3: Implement due-game query and DM loop**

Due condition:

```sql
active = 1
AND reminder_sent = 0
AND start_ts > :now_ts
AND start_ts <= :now_ts + (:reminder_hours * 3600)
```

Reminder text:

```text
🎲 Game Reminder

You're signed up for **{title}**.
Starts: <t:{start_ts}:F> (<t:{start_ts}:R>)
```

If `channel_id` and `message_id` exist, append:

```text
https://discord.com/channels/{guild_id}/{channel_id}/{message_id}
```

Catch `discord.Forbidden`, `discord.HTTPException`, and unexpected per-user exceptions; log them and continue. Mark the game sent after the batch finishes, even if one or more DMs failed.

Provide a tiny async wrapper so tests can patch marking cleanly:

```python
async def mark_sent(db_path: Path, game_id: int) -> None:
    database.mark_reminder_sent(db_path, game_id)
```

- [ ] **Step 4: Run reminder tests**

```bash
pytest tests/test_reminders.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add database.py reminders.py tests/test_reminders.py
git commit -m "feat: add eight-hour dm reminders"
```

---

### Task 7: Bot Startup Wiring and Persistent Restoration

**Files:**
- Create: `bot.py`
- Create: `tests/test_startup.py`

**Interfaces:**
- Consumes: all prior modules.
- Produces: runnable entry point `python bot.py`.

- [ ] **Step 1: Write a failing startup guard test**

```python
# tests/test_startup.py
import pytest

import bot


def test_require_token_rejects_empty_value():
    with pytest.raises(RuntimeError, match="DISCORD_BOT_TOKEN"):
        bot.require_token("")
```

- [ ] **Step 2: Run test and confirm failure**

```bash
pytest tests/test_startup.py -v
```

Expected: FAIL because `bot.py` does not exist.

- [ ] **Step 3: Implement startup wiring**

Core structure:

```python
import asyncio
import time

import discord
from discord.ext import commands

import config
import database
from game_commands import register_game_commands
from game_views import restore_views
from reminders import start_reminder_loop


def require_token(token: str) -> str:
    if not token:
        raise RuntimeError("DISCORD_BOT_TOKEN is missing. Copy .env.example to .env and add your bot token.")
    return token


class GameBoardBot(commands.Bot):
    async def setup_hook(self) -> None:
        database.init_db(config.DATABASE_PATH)
        register_game_commands(self.tree, config.DATABASE_PATH)
        await restore_views(self, config.DATABASE_PATH, int(time.time()))
        await self.tree.sync()
        start_reminder_loop(self, config.DATABASE_PATH)


intents = discord.Intents.default()
bot = GameBoardBot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")


if __name__ == "__main__":
    bot.run(require_token(config.BOT_TOKEN))
```

Ensure reminder-loop startup is idempotent so reconnects do not start duplicate loops.

- [ ] **Step 4: Run startup test and full suite**

```bash
pytest tests/test_startup.py -v
pytest -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add bot.py tests/test_startup.py
git commit -m "feat: wire bot startup and persistent views"
```

---

### Task 8: Beginner-Friendly Setup Documentation and Manual Smoke Test

**Files:**
- Create: `README.md`
- Create: `.gitignore`

**Interfaces:**
- Produces: exact setup path for a non-expert maintainer.

- [ ] **Step 1: Add safe git ignores**

```text
# .gitignore
.env
.venv/
__pycache__/
.pytest_cache/
data/games.db
*.pyc
```

- [ ] **Step 2: Write README with exact commands**

README must include these copy/paste steps:

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python bot.py
```

macOS/Linux:

```bash
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python bot.py
```

Also document Discord Developer Portal setup:
1. Create Application.
2. Add Bot.
3. Copy token into `.env` as `DISCORD_BOT_TOKEN=...`.
4. OAuth2 URL Generator scopes: `bot`, `applications.commands`.
5. Bot permissions: View Channels, Send Messages, Embed Links, Read Message History.
6. Invite bot to the server.
7. Run `python bot.py`.
8. Use `/create-game` in a channel where the bot has permissions.

Include a troubleshooting section for:
- slash command not visible: restart bot and wait briefly after sync;
- `DISCORD_BOT_TOKEN is missing`: verify `.env` file name and token line;
- bot cannot post: verify channel permissions;
- player receives no reminder: DMs may be disabled; V1 intentionally has no channel fallback.

- [ ] **Step 3: Run automated verification**

```bash
python -m compileall .
pytest -v
```

Expected: compile succeeds and all tests pass.

- [ ] **Step 4: Run a manual Discord smoke test**

In a test server:
1. Create a game with `max_players=1` and a future Eastern time.
2. Click Sign Up; verify `Players: 1 / 1` and disabled Sign Up button.
3. Click Sign Up again; verify ephemeral duplicate/full feedback without changing count.
4. Click Withdraw; verify `Players: 0 / 1` and Sign Up re-enabled.
5. Restart the bot; verify the existing buttons still work.
6. Temporarily create a test game within the reminder window and verify only the registered user receives a DM.

- [ ] **Step 5: Commit**

```bash
git add README.md .gitignore
git commit -m "docs: add beginner setup and smoke test guide"
```

---

## Final Verification

- [ ] Run the complete test suite:

```bash
pytest -v
```

- [ ] Run syntax compilation:

```bash
python -m compileall .
```

- [ ] Confirm git working tree is clean:

```bash
git status --short
```

- [ ] Confirm the README setup works from a fresh virtual environment.
- [ ] Confirm `/create-game` posts a functional embed with dynamic timestamps.
- [ ] Confirm signups cannot exceed max players.
- [ ] Confirm withdrawal reopens a full game.
- [ ] Confirm restarting the bot preserves button functionality.
- [ ] Confirm reminders are sent once, by DM only, and a failed DM does not stop other reminders.
