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
        raise RuntimeError(
            "DISCORD_BOT_TOKEN is missing. Copy .env.example to .env and add your bot token."
        )
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
