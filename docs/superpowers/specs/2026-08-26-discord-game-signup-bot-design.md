# Discord Game Signup Bot — V1 Design

## Goal
Create a simple Discord bot that lets an organizer post game advertisements, allows players to sign up or withdraw with buttons, enforces a maximum player count, and sends signed-up players a private reminder 8 hours before the game.

## Priorities
1. Smooth operation for a non-expert maintainer.
2. Minimal setup and dependencies.
3. Reliable persistence across bot restarts.
4. Clear, readable code with features separated by responsibility.

## Technology
- Python 3.12+
- discord.py 2.x
- SQLite via Python's built-in sqlite3 module
- python-dotenv for the bot token and simple configuration
- zoneinfo from the Python standard library for Eastern Time handling

No external database or web service is required for V1.

## Command
### /create-game
Inputs:
- title: string
- max_players: integer
- description: string
- date: string in YYYY-MM-DD format
- time: string in HH:MM 24-hour format
- image: Discord attachment

All entered dates and times are interpreted in the `America/New_York` timezone. This automatically handles EST/EDT daylight-saving transitions.

Validation:
- max_players must be at least 1
- date/time must parse successfully
- game time must be in the future
- image is optional if Discord command limitations make attachment handling awkward; preferred behavior is to support it directly

## Public Game Post
The bot posts a Discord embed containing:
- title
- description
- image
- Discord native dynamic timestamp for the game start
- relative timestamp such as "in 3 days"
- player count in the form `Players: X / Max`

Buttons:
- `✅ Sign Up`
- `❌ Withdraw`

When full:
- status changes to `🔴 FULL — Players: Max / Max`
- Sign Up button becomes disabled
- Withdraw remains available

When a player withdraws from a full game:
- their signup is removed
- count is refreshed
- Sign Up becomes enabled again

The public post does not display player names in V1.

## Signup Rules
- A Discord user may sign up only once per game.
- A user may withdraw only if currently signed up.
- Signups are rejected once the game is full.
- Signups are rejected once the game has started.
- Button responses should be ephemeral so only the clicking user sees confirmation/error messages.

## Persistence
Use one SQLite database file: `data/games.db`.

### games table
Stores:
- game ID
- guild ID
- channel ID
- message ID
- creator user ID
- title
- description
- image URL
- maximum players
- start timestamp in UTC
- reminder-sent flag
- active/cancelled state if needed for safe handling

### signups table
Stores:
- game ID
- Discord user ID
- signup timestamp

A unique constraint on `(game_id, user_id)` prevents duplicate signups.

## Persistent Discord Buttons
Buttons must continue working after a bot restart.

Use persistent `discord.ui.View` components with stable custom IDs containing the game ID. On startup, the bot reloads active future games from SQLite and re-registers their views.

## Reminder System
A lightweight background task runs every 5 minutes.

For each active game:
- if the game begins within 8 hours
- and the reminder has not already been sent
- retrieve all signed-up user IDs
- send each user a DM reminder
- catch and ignore individual DM failures so one blocked DM does not stop the others
- mark the game's reminder as sent after the reminder batch is processed

Reminder content includes:
- game title
- game start time using Discord's dynamic timestamp
- relative start time
- optional link back to the signup post

No server-channel fallback is used when DMs fail.

## Concurrency / Full-Game Protection
Two players may click Sign Up at nearly the same moment. Signup handling must re-check player count inside the database write path before inserting a signup.

A per-game asyncio lock is sufficient for V1 because the bot runs as a single process. This prevents the signup count from temporarily exceeding max players.

## File Structure
```
discord-game-board/
├── bot.py
├── config.py
├── database.py
├── game_commands.py
├── game_views.py
├── reminders.py
├── requirements.txt
├── .env.example
├── README.md
└── data/
    └── games.db
```

### bot.py
Starts the bot, registers commands/views, and starts reminder checks.

### config.py
Loads environment variables and timezone settings.

### database.py
Owns database initialization and all game/signup queries.

### game_commands.py
Implements `/create-game`.

### game_views.py
Implements Sign Up / Withdraw buttons and embed refresh logic.

### reminders.py
Implements the periodic 8-hour DM reminder task.

## Error Handling
User-facing errors should be short and understandable:
- `You're already signed up for this game.`
- `This game is full.`
- `You aren't signed up for this game.`
- `This game has already started.`
- `I couldn't create that game. Check the date and time and try again.`

Unexpected exceptions are logged to the terminal with enough detail to debug without exposing technical errors in the public Discord channel.

## Setup Experience
V1 should require only:
1. Install Python.
2. Install dependencies with `pip install -r requirements.txt`.
3. Create a Discord application/bot in the Developer Portal.
4. Put the token in `.env`.
5. Invite the bot with the required scopes/permissions.
6. Run `python bot.py`.

The README should include exact copy/paste setup commands.

## Testing
Tests should focus on behavior that is easy to break:
- duplicate signup rejected
- signup count cannot exceed max players
- withdrawal reopens a full game
- Eastern Time converts correctly to UTC
- DST dates are handled correctly
- reminder sends only once
- DM failure for one user does not interrupt other reminders
- persistent views are restored from the database

## Deferred Features
Not part of V1:
- View Players button
- waitlist
- interactive game-creation wizard
- edit/cancel commands
- multiple creator timezones
- web dashboard
- external database

The database/API boundaries should leave room for these later without changing the core signup model.
