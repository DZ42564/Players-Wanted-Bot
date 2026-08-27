from game_commands import parse_game_target


def test_parse_game_target_accepts_message_id():
    assert parse_game_target("123456789012345678") == 123456789012345678


def test_parse_game_target_accepts_discord_message_link():
    link = "https://discord.com/channels/1/2/123456789012345678"
    assert parse_game_target(link) == 123456789012345678
