import logging
import time
from pathlib import Path

import discord
from discord.ext import tasks

import database
from config import REMINDER_HOURS, REMINDER_POLL_SECONDS
from game_commands import build_game_embed

log = logging.getLogger(__name__)


async def mark_sent(db_path: Path, game_id: int) -> None:
    database.mark_reminder_sent(db_path, game_id)


def build_reminder_text(game: dict, server_name: str | None = None) -> str:
    text = "🎲 **Game Reminder**\n\n" f"You're signed up for **{game['title']}**.\n"
    if server_name:
        text += f"Server: **{server_name}**\n"
    text += f"Starts: <t:{game['start_ts']}:F> (<t:{game['start_ts']}:R>)"
    if game.get("guild_id") and game.get("channel_id") and game.get("message_id"):
        text += "\n\n**Jump to game post:**\n" f"https://discord.com/channels/{game['guild_id']}/{game['channel_id']}/{game['message_id']}"
    return text


def build_cancellation_text(game: dict, server_name: str | None = None) -> str:
    text = "❌ **Game Cancelled**\n\n" f"**{game['title']}** has been cancelled."
    if server_name:
        text += f"\nServer: **{server_name}**"
    text += f"\nOriginal time: <t:{game['start_ts']}:F>"
    return text


async def _server_name(bot: discord.Client, guild_id: int) -> str | None:
    guild = bot.get_guild(guild_id) if hasattr(bot, "get_guild") else None
    return getattr(guild, "name", None)


async def send_due_reminders(bot: discord.Client, db_path: Path, now_ts: int) -> None:
    games = database.get_games_due_for_reminder(db_path, now_ts, REMINDER_HOURS)
    for game in games:
        message = build_reminder_text(game, await _server_name(bot, game["guild_id"]))
        for user_id in database.list_signup_user_ids(db_path, game["id"]):
            try:
                user = await bot.fetch_user(user_id)
                await user.send(message)
            except (discord.Forbidden, discord.HTTPException) as exc:
                log.warning("Could not DM reminder for game %s to user %s: %s", game["id"], user_id, exc)
            except Exception:
                log.exception("Unexpected error DMing reminder for game %s to user %s", game["id"], user_id)
        await mark_sent(db_path, game["id"])


async def send_cancellation_notices(bot: discord.Client, db_path: Path, game: dict, server_name: str | None = None) -> None:
    message = build_cancellation_text(game, server_name)
    for user_id in database.list_signup_user_ids(db_path, game["id"]):
        try:
            user = await bot.fetch_user(user_id)
            await user.send(message)
        except (discord.Forbidden, discord.HTTPException) as exc:
            log.warning("Could not DM cancellation for game %s to user %s: %s", game["id"], user_id, exc)
        except Exception:
            log.exception("Unexpected error DMing cancellation for game %s to user %s", game["id"], user_id)


async def close_past_game_posts(bot: discord.Client, db_path: Path, now_ts: int) -> None:
    for game_id in database.close_past_games(db_path, now_ts):
        game = database.get_game(db_path, game_id)
        if game is None or not game.get("message_id"):
            continue
        try:
            channel = bot.get_channel(game["channel_id"])
            if channel is None:
                channel = await bot.fetch_channel(game["channel_id"])
            message = await channel.fetch_message(game["message_id"])
            from game_views import GameSignupView
            await message.edit(
                embed=build_game_embed(game, database.count_signups(db_path, game_id)),
                view=GameSignupView(game_id, db_path),
            )
        except (discord.Forbidden, discord.HTTPException):
            log.warning("Could not update closed game post %s", game_id)
        except Exception:
            log.exception("Unexpected error updating closed game post %s", game_id)


def start_reminder_loop(bot: discord.Client, db_path: Path):
    existing = getattr(bot, "_game_board_reminder_loop", None)
    if existing is not None and existing.is_running():
        return existing

    @tasks.loop(seconds=REMINDER_POLL_SECONDS)
    async def reminder_loop():
        now_ts = int(time.time())
        await close_past_game_posts(bot, db_path, now_ts)
        await send_due_reminders(bot, db_path, now_ts)

    reminder_loop.start()
    setattr(bot, "_game_board_reminder_loop", reminder_loop)
    return reminder_loop
