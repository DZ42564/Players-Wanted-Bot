import pytest

import bot


def test_require_token_rejects_empty_value():
    with pytest.raises(RuntimeError, match="DISCORD_BOT_TOKEN"):
        bot.require_token("")
