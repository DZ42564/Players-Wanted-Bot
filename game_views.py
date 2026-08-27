import asyncio
import time
from pathlib import Path

import discord

import database
from game_commands import build_game_embed

_game_locks: dict[int, asyncio.Lock] = {}


def get_game_lock(game_id: int) -> asyncio.Lock:
    return _game_locks.setdefault(game_id, asyncio.Lock())


class GameSignupView(discord.ui.View):
    def __init__(self, game_id: int, db_path: Path):
        super().__init__(timeout=None)
        self.game_id = game_id
        self.db_path = db_path

        self.signup_button = discord.ui.Button(label="Sign Up", style=discord.ButtonStyle.success, custom_id=f"game:{game_id}:signup")
        self.withdraw_button = discord.ui.Button(label="Withdraw", style=discord.ButtonStyle.danger, custom_id=f"game:{game_id}:withdraw")
        self.view_players_button = discord.ui.Button(label="View Players", style=discord.ButtonStyle.secondary, custom_id=f"game:{game_id}:players")
        self.signup_button.callback = self._signup
        self.withdraw_button.callback = self._withdraw
        self.view_players_button.callback = self._view_players
        self.add_item(self.signup_button)
        self.add_item(self.withdraw_button)
        self.add_item(self.view_players_button)
        self._apply_state()

    def _apply_state(self) -> None:
        game = database.get_game(self.db_path, self.game_id)
        if game is None:
            return
        signup_count = database.count_signups(self.db_path, self.game_id)
        inactive = game.get("status", "active") != "active" or int(time.time()) >= game["start_ts"]
        self.signup_button.disabled = inactive or signup_count >= game["max_players"]
        self.withdraw_button.disabled = inactive

    async def _refresh_message(self, interaction: discord.Interaction) -> None:
        game = database.get_game(self.db_path, self.game_id)
        if game is None:
            return
        signup_count = database.count_signups(self.db_path, self.game_id)
        self._apply_state()
        if interaction.message is not None:
            await interaction.message.edit(embed=build_game_embed(game, signup_count), view=self)

    async def _signup(self, interaction: discord.Interaction) -> None:
        async with get_game_lock(self.game_id):
            result = database.try_add_signup(self.db_path, self.game_id, interaction.user.id, int(time.time()))
            messages = {
                "added": "You're signed up!",
                "duplicate": "You're already signed up for this game.",
                "full": "This game is already full.",
                "started": "This game has already started.",
                "missing": "This game is no longer available.",
            }
            await interaction.response.send_message(messages[result], ephemeral=True)
            if result == "added":
                await self._refresh_message(interaction)

    async def _withdraw(self, interaction: discord.Interaction) -> None:
        async with get_game_lock(self.game_id):
            result = database.remove_signup(self.db_path, self.game_id, interaction.user.id)
            messages = {
                "removed": "You've withdrawn from this game.",
                "not_signed_up": "You aren't signed up for this game.",
                "missing": "This game is no longer available.",
            }
            await interaction.response.send_message(messages[result], ephemeral=True)
            if result == "removed":
                await self._refresh_message(interaction)

    async def _view_players(self, interaction: discord.Interaction) -> None:
        game = database.get_game(self.db_path, self.game_id)
        if game is None:
            await interaction.response.send_message("I couldn't find this game anymore.", ephemeral=True)
            return
        user_ids = database.list_signup_user_ids(self.db_path, self.game_id)
        if user_ids:
            roster = "\n".join(f"{index}. <@{user_id}>" for index, user_id in enumerate(user_ids, 1))
        else:
            roster = "No players are signed up yet."
        text = f"**Players — {game['title']}**\n\n{roster}\n\n**{len(user_ids)} / {game['max_players']} players**"
        await interaction.response.send_message(text, ephemeral=True, allowed_mentions=discord.AllowedMentions.none())


async def restore_views(bot: discord.Client, db_path: Path, now_ts: int) -> None:
    for game in database.get_games_with_messages(db_path):
        bot.add_view(GameSignupView(game["id"], db_path))
