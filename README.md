# Discord Game Signup Board — V1.1

A small Discord bot for posting game advertisements, managing signups, showing a private roster, pinging an optional role, and sending DM reminders.

## What's new in V1.1

- **View Players** button: anyone can privately see the current roster without cluttering the public channel.
- Optional **Role** field on `/create-game` so a game can ping the appropriate server role.
- `/edit-game` can change only the fields you need without recreating the event.
- `/cancel-game` keeps the post visible, marks it cancelled, disables signup controls, and DMs registered players.
- Past games automatically become **CLOSED**.
- Game-management commands are restricted to the configured moderator role, server Administrators, and the server owner.
- Reminder DMs now include the server name and a jump link back to the game post.
- `tzdata` is included so Eastern Time works correctly on Windows.
- Existing V1 `data/games.db` files are upgraded automatically; do **not** delete your database when upgrading.

## Permissions used on your server

For this server, the configured game-manager role is:

```text
FORGE WARDENS (MODS)
Role ID: 1108109214628450314
```

The server owner and anyone with Discord's **Administrator** permission can also manage games automatically.

## 1. Install Python

Install **Python 3.12 or newer**. Python 3.13 also works.

On Windows, enable **Add Python to PATH** during installation.

## 2. Create/invite the Discord application

If V1 is already in your server, you do not need to recreate the application.

The bot invite needs these scopes:

- `bot`
- `applications.commands`

Recommended bot permissions:

- View Channels
- Send Messages
- Embed Links
- Read Message History
- **Mention @everyone, @here, and All Roles** if you want it to ping roles that are not marked mentionable

You do **not** need Message Content Intent for this bot.

## 3. Upgrade from V1 on Windows

1. Stop the old bot with `Ctrl+C`.
2. Back up `data/games.db` somewhere safe.
3. Replace the old Python files with the V1.1 files, but keep your existing `.env` and `data/games.db`.
4. Open PowerShell in the bot folder.
5. Activate the existing virtual environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

6. Install/update dependencies:

```powershell
pip install -r requirements.txt
```

7. Open `.env` and make sure it contains both lines:

```text
DISCORD_BOT_TOKEN=your_existing_bot_token
GAME_MANAGER_ROLE_ID=1108109214628450314
```

8. Start the bot:

```powershell
python bot.py
```

On startup, V1.1 automatically adds the new database fields while preserving existing games and signups.

## 4. Fresh Windows setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env`:

```text
DISCORD_BOT_TOKEN=your_token_goes_here
GAME_MANAGER_ROLE_ID=1108109214628450314
```

Then run:

```powershell
python bot.py
```

Leave that PowerShell window open while you want the locally hosted bot online.

## `/create-game`

Only a Forge Warden, Administrator, or the server owner can use this command.

Fields:

```text
Title: No Laughing Matter
Max Players: 6
Description: The goblin tribes have suddenly become organized...
Date: 2026-10-17
Time: 19:00
Image: optional
Role: optional role to ping
```

Dates and times are entered in **Eastern Time** (`America/New_York`). Discord dynamic timestamps automatically show each player the correct local time.

If a role is selected, the role mention appears above the game advertisement and is pinged when the game is first posted.

## Player buttons

### Sign Up

Adds the player if space remains. Duplicate signups are rejected. At capacity the post shows `FULL` and Sign Up disables.

### Withdraw

Removes the clicking player and reopens a slot if necessary.

### View Players

Shows only the clicking user an ephemeral roster such as:

```text
Players — No Laughing Matter

1. @PlayerOne
2. @PlayerTwo
3. @PlayerThree

3 / 6 players
```

View Players remains usable after a game is cancelled or closed.

## `/edit-game`

Only game managers can use this command.

`target` accepts either:

- the Discord message link for the game post, or
- the message ID

Every other field is optional. Leave a field blank to keep its current value.

Editable fields:

- title
- max players
- description
- date
- time
- image
- role
- clear role

Changing the date/time resets the 8-hour reminder so the reminder can be sent for the new schedule. The bot will not allow the maximum player count to be reduced below the number of players already signed up.

Changing a role on an existing post updates the visible role mention **without pinging the role a second time**.

## `/cancel-game`

Provide the game post link or message ID.

The bot will:

1. Mark the existing post **CANCELLED**.
2. Disable Sign Up and Withdraw.
3. Keep View Players available.
4. DM everyone currently signed up that the game was cancelled.
5. Leave the public post in place as a record.

DM failures are isolated; one player blocking DMs does not prevent other players from receiving cancellation notices.

## Automatic closing

Once a game's start time passes, V1.1 marks it:

```text
🔒 CLOSED — Players: X / Max
```

Sign Up and Withdraw are disabled. The roster remains viewable.

## Reminders

Every five minutes the bot checks for active games beginning within the next 8 hours.

Registered players receive a private DM containing:

- game title
- server name
- Discord-localized start time
- relative time
- jump link to the signup post

The reminder is sent once per scheduled game time. Editing the game date/time resets the reminder flag.

## Data and restarts

Persistent data lives in:

```text
data/games.db
```

**Do not delete this file during a V1 → V1.1 upgrade.**

Buttons are persistent and are re-registered after bot restarts, including View Players on cancelled/closed games.

## Finding a message link

Right-click the game post and choose **Copy Message Link**. Paste that into the `target` field for `/edit-game` or `/cancel-game`.

If you prefer message IDs, enable **User Settings → Advanced → Developer Mode**, then right-click the message and choose **Copy Message ID**.

## Troubleshooting

### Commands do not appear

Confirm the bot was invited with `applications.commands`. Check **Server Settings → Integrations → Player's Wanted** to see whether the commands are registered, then refresh Discord with `Ctrl+R`.

### `No module named 'tzdata'`

Run inside the activated virtual environment:

```powershell
pip install -r requirements.txt
```

V1.1 includes `tzdata` permanently in `requirements.txt`.

### Role text appears but nobody gets pinged

Either make the target role mentionable in **Server Settings → Roles**, or give the bot the **Mention @everyone, @here, and All Roles** permission.

### A Forge Warden is denied access

Verify `.env` contains:

```text
GAME_MANAGER_ROLE_ID=1108109214628450314
```

Then restart the bot.

### The bot goes offline

When hosted on your PC, the bot goes offline if the Python process stops or the PC sleeps/shuts down.

## Developer verification

```powershell
python -m pytest -v
python -m compileall bot.py config.py database.py game_commands.py game_views.py reminders.py
```
