# Discord Game Signup Bot V1.1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend V1 with roster viewing, role pings, management commands, lifecycle closing, permissions, and improved DMs without losing existing data.

**Architecture:** Retain the current `discord.py` + SQLite structure. Add backward-compatible schema migration and focused helpers for authorization, game lookup/update, lifecycle refresh, and DM delivery.

**Tech Stack:** Python 3.12+, discord.py 2.x, SQLite, python-dotenv, zoneinfo/tzdata, pytest.

**Spec:** `docs/superpowers/specs/2026-08-26-discord-game-signup-bot-v1.1-design.md`

## Global Constraints
- Preserve existing V1 database contents.
- `GAME_MANAGER_ROLE_ID=1108109214628450314` is configurable via `.env`.
- Server owner and Administrator always have management access.
- View Players responses are ephemeral.
- Cancelled/closed games remain visible and roster-viewable.
- Reminder cadence remains 8 hours with 5-minute polling.

---

### Task 1: Configuration and database migration
**Files:** `config.py`, `database.py`, `.env.example`, `requirements.txt`, `tests/test_config.py`, `tests/test_database.py`
- [ ] Add failing tests for role config, tzdata dependency, migration fields, game lookup by message, status transitions, and updates.
- [ ] Run tests and verify failure.
- [ ] Implement minimal config/database changes.
- [ ] Run tests and verify pass.

### Task 2: Permissions and game presentation
**Files:** `game_commands.py`, `game_views.py`, `tests/test_permissions.py`, `tests/test_views.py`
- [ ] Add failing tests for owner/admin/role authorization, lifecycle display, and View Players.
- [ ] Run tests and verify failure.
- [ ] Implement permission helper, lifecycle-aware embed/view, and ephemeral roster.
- [ ] Run tests and verify pass.

### Task 3: Create/edit/cancel commands and role ping
**Files:** `game_commands.py`, `database.py`, `reminders.py`, `tests/test_game_management.py`
- [ ] Add failing tests for target parsing, optional edits, cancellation state, and safe role mention behavior.
- [ ] Run tests and verify failure.
- [ ] Implement command behaviors and cancellation DM helper.
- [ ] Run tests and verify pass.

### Task 4: Automatic closing, reminders, startup, docs
**Files:** `game_views.py`, `reminders.py`, `bot.py`, `README.md`, `tests/test_reminders.py`, `tests/test_startup.py`
- [ ] Add failing tests for closing past games and richer reminder text.
- [ ] Run tests and verify failure.
- [ ] Implement closing loop/startup integration and update beginner setup docs.
- [ ] Run full suite, compile all Python files, and package V1.1 ZIP.
