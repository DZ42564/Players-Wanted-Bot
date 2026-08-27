# Discord Game Signup Bot — V1.1 Design

## Goal
Extend the working V1 bot with moderator-gated game management, roster viewing, optional role pings, editing/cancellation, automatic closing of past games, and richer DMs while preserving existing SQLite data.

## Permissions
- `/create-game`: server owner, Administrator, or configured `GAME_MANAGER_ROLE_ID`.
- `/edit-game`: same manager permissions. Original creator remains recorded for audit/reference.
- `/cancel-game`: same manager permissions.
- Sign Up, Withdraw, View Players: available to all server members while appropriate for game status.
- Configured manager role: `1108109214628450314` by default in `.env.example` as an example value the user can keep for this server.

## Commands
- `/create-game`: existing fields plus optional Discord role selector `role`.
- `/edit-game`: target game by Discord message link or message ID; optional editable fields are title, max_players, description, date, time, image, role, and clear_role. Blank values remain unchanged.
- `/cancel-game`: target game by message link or message ID; mark cancelled, update post, disable signup/withdraw, and DM current signups.

## Buttons
- Sign Up
- Withdraw
- View Players: ephemeral roster with mentions and `X / Max` count.
- View Players remains usable for cancelled/closed games.

## Game lifecycle
- `active`: signup and withdrawal allowed until start time.
- `cancelled`: signup and withdrawal disabled; roster view remains.
- `closed`: applied automatically after start time; signup and withdrawal disabled; roster view remains.

## Persistence and migration
Existing V1 databases are upgraded in place. Add `status TEXT NOT NULL DEFAULT 'active'` and `ping_role_id INTEGER` if missing. Preserve the existing `active` column for backward compatibility during migration, but V1.1 logic uses `status`.

## Reminder/cancellation DMs
8-hour reminder contains title, dynamic timestamp, server name when available, and jump link. Cancellation sends a DM to each current signup; one DM failure never blocks the rest.

## Deployment
Keep Python/discord.py/SQLite architecture. Add `tzdata` to requirements for reliable Windows timezone support. `.env` gains `GAME_MANAGER_ROLE_ID`.
