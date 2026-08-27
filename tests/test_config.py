from pathlib import Path

import config


def test_config_constants():
    assert config.DATABASE_PATH == Path("data/games.db")
    assert config.EASTERN_TZ.key == "America/New_York"
    assert config.REMINDER_HOURS == 8
    assert config.REMINDER_POLL_SECONDS == 300
    assert config.GAME_MANAGER_ROLE_ID == 1108109214628450314
