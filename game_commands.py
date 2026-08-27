import re
from datetime import datetime, timezone
from pathlib import Path

import discord

import database
from config import EASTERN_TZ, GAME_MANAGER_ROLE_ID


def parse_eastern_datetime(date_text: str, time_text: str) -> int:
    naive = datetime.strptime(f"{date_text} {time_text}", "%Y-%m-%d %H:%M")
    eastern = naive.replace(tzinfo=EASTERN_TZ)
    return int(eastern.astimezone(timezone.utc).timestamp())


def format_player_status(signup_count: int, max_players: int, status: str = "active") -> str:
    if status == "cancelled":
        return f"❌ CANCELLED — Players: {signup_count} / {max_players}"
    if status == "closed":
        return f"🔒 CLOSED — Players: {signup_count} / {max_players}"
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
        value=format_player_status(signup_count, game["max_players"], game.get("status", "active")),
        inline=False,
    )
    if game.get("image_url"):
        embed.set_image(url=game["image_url"])
    return embed


def validate_game_input(max_players: int, start_ts: int, now_ts: int) -> None:
    if max_players < 1:
        raise ValueError("max_players must be at least 1")
    if start_ts <= now_ts:
        raise ValueError("game time must be in the future")


def can_manage_games(interaction: discord.Interaction, manager_role_id: int = GAME_MANAGER_ROLE_ID) -> bool:
    guild = getattr(interaction, "guild", None)
    user = getattr(interaction, "user", None)
    if guild is None or user is None:
        return False
    if getattr(guild, "owner_id", None) == getattr(user, "id", None):
        return True
    perms = getattr(user, "guild_permissions", None)
    if perms is not None and getattr(perms, "administrator", False):
        return True
    return any(getattr(role, "id", None) == manager_role_id for role in getattr(user, "roles", []))


def parse_game_target(target: str) -> int:
    target = target.strip()
    if target.isdigit():
        return int(target)
    match = re.search(r"/channels/\d+/\d+/(\d+)(?:/)?$", target)
    if match:
        return int(match.group(1))
    raise ValueError("Use a Discord message link or message ID.")


def _edited_start_ts(game: dict, date: str | None, time: str | None) -> int | None:
    if date is None and time is None:
        return None
    current = datetime.fromtimestamp(game["start_ts"], timezone.utc).astimezone(EASTERN_TZ)
    date_text = date or current.strftime("%Y-%m-%d")
    time_text = time or current.strftime("%H:%M")
    return parse_eastern_datetime(date_text, time_text)


async def _get_game_message(interaction: discord.Interaction, game: dict):
    client = interaction.client
    channel = client.get_channel(game["channel_id"])
    if channel is None:
        channel = await client.fetch_channel(game["channel_id"])
    return await channel.fetch_message(game["message_id"])


def register_game_commands(tree: discord.app_commands.CommandTree, db_path: Path) -> None:
    @tree.command(name="create-game", description="Create a game signup post")
    @discord.app_commands.describe(
        title="Game title",
        max_players="Maximum number of players",
        description="Game description",
        date="Game date in YYYY-MM-DD format (Eastern Time)",
        time="Game time in HH:MM 24-hour format (Eastern Time)",
        image="Optional advertisement image",
        role="Optional role to ping when the game is posted",
    )
    async def create_game(
        interaction: discord.Interaction,
        title: str,
        max_players: int,
        description: str,
        date: str,
        time: str,
        image: discord.Attachment | None = None,
        role: discord.Role | None = None,
    ) -> None:
        await interaction.response.defer(ephemeral=True)
        if interaction.guild_id is None or interaction.channel is None:
            await interaction.followup.send("Please use this command inside a server channel.", ephemeral=True)
            return
        if not can_manage_games(interaction):
            await interaction.followup.send("Only Forge Wardens, Administrators, or the server owner can create games.", ephemeral=True)
            return
        try:
            start_ts = parse_eastern_datetime(date, time)
            now_ts = int(datetime.now(timezone.utc).timestamp())
            validate_game_input(max_players, start_ts, now_ts)
        except ValueError:
            await interaction.followup.send(
                "I couldn't create that game. Check the date, time, and player limit and try again.", ephemeral=True
            )
            return

        game_id = database.create_game(
            path=db_path,
            guild_id=interaction.guild_id,
            channel_id=interaction.channel_id,
            creator_user_id=interaction.user.id,
            title=title,
            description=description,
            image_url=image.url if image else None,
            max_players=max_players,
            start_ts=start_ts,
            ping_role_id=role.id if role else None,
        )
        game = database.get_game(db_path, game_id)
        from game_views import GameSignupView
        content = role.mention if role else None
        allowed_mentions = discord.AllowedMentions(roles=[role]) if role else discord.AllowedMentions.none()
        message = await interaction.channel.send(
            content=content,
            embed=build_game_embed(game, 0),
            view=GameSignupView(game_id, db_path),
            allowed_mentions=allowed_mentions,
        )
        database.set_message_id(db_path, game_id, message.id)
        await interaction.followup.send(f"Created **{title}** successfully.", ephemeral=True)

    @tree.command(name="edit-game", description="Edit an existing game signup post")
    @discord.app_commands.describe(
        target="Game post message link or message ID",
        title="New title; leave blank to keep current",
        max_players="New player limit; leave blank to keep current",
        description="New description; leave blank to keep current",
        date="New date YYYY-MM-DD Eastern; leave blank to keep current",
        time="New time HH:MM Eastern; leave blank to keep current",
        image="New image; leave blank to keep current",
        role="New role shown on the post",
        clear_role="Remove the role from the post",
    )
    async def edit_game(
        interaction: discord.Interaction,
        target: str,
        title: str | None = None,
        max_players: int | None = None,
        description: str | None = None,
        date: str | None = None,
        time: str | None = None,
        image: discord.Attachment | None = None,
        role: discord.Role | None = None,
        clear_role: bool = False,
    ) -> None:
        await interaction.response.defer(ephemeral=True)
        if interaction.guild_id is None or not can_manage_games(interaction):
            await interaction.followup.send("You don't have permission to edit games.", ephemeral=True)
            return
        try:
            message_id = parse_game_target(target)
        except ValueError as exc:
            await interaction.followup.send(str(exc), ephemeral=True)
            return
        game = database.get_game_by_message_id(db_path, interaction.guild_id, message_id)
        if game is None:
            await interaction.followup.send("I couldn't find a game post with that message ID in this server.", ephemeral=True)
            return
        if game["status"] != "active":
            await interaction.followup.send("Cancelled or closed games can't be edited.", ephemeral=True)
            return
        if role is not None and clear_role:
            await interaction.followup.send("Choose a role or clear the role, not both.", ephemeral=True)
            return
        if max_players is not None and max_players < database.count_signups(db_path, game["id"]):
            await interaction.followup.send("The new player limit can't be lower than the number already signed up.", ephemeral=True)
            return
        updates = {}
        if title is not None:
            updates["title"] = title
        if description is not None:
            updates["description"] = description
        if max_players is not None:
            if max_players < 1:
                await interaction.followup.send("The player limit must be at least 1.", ephemeral=True)
                return
            updates["max_players"] = max_players
        if image is not None:
            updates["image_url"] = image.url
        if role is not None:
            updates["ping_role_id"] = role.id
        elif clear_role:
            updates["ping_role_id"] = None
        try:
            new_start = _edited_start_ts(game, date, time)
            if new_start is not None:
                validate_game_input(updates.get("max_players", game["max_players"]), new_start, int(datetime.now(timezone.utc).timestamp()))
                updates["start_ts"] = new_start
                updates["reminder_sent"] = 0
        except ValueError:
            await interaction.followup.send("I couldn't understand the new date/time. Use YYYY-MM-DD and HH:MM Eastern.", ephemeral=True)
            return
        database.update_game(db_path, game["id"], **updates)
        game = database.get_game(db_path, game["id"])
        message = await _get_game_message(interaction, game)
        selected_role = interaction.guild.get_role(game["ping_role_id"]) if game.get("ping_role_id") else None
        from game_views import GameSignupView
        await message.edit(
            content=selected_role.mention if selected_role else None,
            embed=build_game_embed(game, database.count_signups(db_path, game["id"])),
            view=GameSignupView(game["id"], db_path),
            allowed_mentions=discord.AllowedMentions.none(),
        )
        await interaction.followup.send(f"Updated **{game['title']}**.", ephemeral=True)

    @tree.command(name="cancel-game", description="Cancel a game and notify signed-up players")
    @discord.app_commands.describe(target="Game post message link or message ID")
    async def cancel_game(interaction: discord.Interaction, target: str) -> None:
        await interaction.response.defer(ephemeral=True)
        if interaction.guild_id is None or not can_manage_games(interaction):
            await interaction.followup.send("You don't have permission to cancel games.", ephemeral=True)
            return
        try:
            message_id = parse_game_target(target)
        except ValueError as exc:
            await interaction.followup.send(str(exc), ephemeral=True)
            return
        game = database.get_game_by_message_id(db_path, interaction.guild_id, message_id)
        if game is None:
            await interaction.followup.send("I couldn't find that game post in this server.", ephemeral=True)
            return
        if game["status"] != "active":
            await interaction.followup.send("That game is already cancelled or closed.", ephemeral=True)
            return
        database.set_game_status(db_path, game["id"], "cancelled")
        game = database.get_game(db_path, game["id"])
        message = await _get_game_message(interaction, game)
        selected_role = interaction.guild.get_role(game["ping_role_id"]) if game.get("ping_role_id") else None
        from game_views import GameSignupView
        await message.edit(
            content=selected_role.mention if selected_role else None,
            embed=build_game_embed(game, database.count_signups(db_path, game["id"])),
            view=GameSignupView(game["id"], db_path),
            allowed_mentions=discord.AllowedMentions.none(),
        )
        from reminders import send_cancellation_notices
        await send_cancellation_notices(interaction.client, db_path, game, getattr(interaction.guild, "name", None))
        await interaction.followup.send(f"Cancelled **{game['title']}** and notified the signed-up players by DM.", ephemeral=True)
