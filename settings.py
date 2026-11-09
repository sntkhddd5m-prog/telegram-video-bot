import os
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional
from dotenv import load_dotenv

# Автоматически ищем файл .env или просто env для удобства на iPad
env_path = Path('.env')
if not env_path.exists():
    env_path = Path('env')
load_dotenv(dotenv_path=env_path)

@dataclass(frozen=True)
class Settings:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    REQUIRED_CHANNELS: List[str] = None
    DEFAULT_LANGUAGE: str = os.getenv("DEFAULT_LANGUAGE", "ru")
    DEBUG: bool = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")
    MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "50"))
    DOWNLOAD_TIMEOUT_SECONDS: int = int(os.getenv("DOWNLOAD_TIMEOUT_SECONDS", "180"))
    MAX_CONCURRENT_DOWNLOADS: int = int(os.getenv("MAX_CONCURRENT_DOWNLOADS", "3"))
    MAX_QUEUE_SIZE: int = int(os.getenv("MAX_QUEUE_SIZE", "50"))
    RATE_LIMIT_SECONDS: float = float(os.getenv("RATE_LIMIT_SECONDS", "3.0"))
    USER_MAX_ACTIVE_TASKS: int = int(os.getenv("USER_MAX_ACTIVE_TASKS", "1"))
    TEMP_DIR: str = os.getenv("TEMP_DIR", "/tmp/tg_video_bot")
    PROXY_URL: Optional[str] = os.getenv("PROXY_URL", None)
    COOKIES_FILE: Optional[str] = os.getenv("COOKIES_FILE", None)

    def __post_init__(self):
        raw_channels = os.getenv("REQUIRED_CHANNELS", "@hf_motion")
        channels = [c.strip() for c in raw_channels.split(",") if c.strip()]
        object.__setattr__(self, 'REQUIRED_CHANNELS', channels)

    def validate(self) -> None:
        if not self.BOT_TOKEN or self.BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
            raise ValueError("BOT_TOKEN is not configured!")

settings = Settings()
