import os
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")
DATABASE_PATH = Path("data/games.db")
EASTERN_TZ = ZoneInfo("America/New_York")
REMINDER_HOURS = 8
REMINDER_POLL_SECONDS = 300
GAME_MANAGER_ROLE_ID = int(os.getenv("GAME_MANAGER_ROLE_ID", "1108109214628450314"))
