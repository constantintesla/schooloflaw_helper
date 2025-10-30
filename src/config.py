import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"

load_dotenv(dotenv_path=ROOT_DIR / ".env")


@dataclass(frozen=True)
class Settings:
	bot_token: str = os.getenv("BOT_TOKEN", "")


settings = Settings()

if not settings.bot_token:
	raise RuntimeError("BOT_TOKEN не задан. Создайте .env с BOT_TOKEN=<токен>")
