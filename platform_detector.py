import re
from enum import Enum
from typing import Optional, Tuple

class Platform(str, Enum):
    YOUTUBE = "YouTube"
    INSTAGRAM = "Instagram"
    TIKTOK = "TikTok"
    PINTEREST = "Pinterest"
    UNKNOWN = "Unknown"

YOUTUBE_REGEX = re.compile(r"(https?://)?(www\.|m\.)?(youtube\.com/(?:watch\?[^\s]*v=|shorts/|v/|live/)|youtu\.be/)([\w-]{11})([^\s]*)", re.IGNORECASE)
INSTAGRAM_REGEX = re.compile(r"(https?://)?(www\.)?(instagram\.com|instagr\.am)/(p|reel|tv|reels)/([A-Za-z0-9_-]+)/?([^\s]*)", re.IGNORECASE)
TIKTOK_REGEX = re.compile(r"(https?://)?((?:www|vm|vt|m)\.)?tiktok\.com/(@[\w.-]+/video/\d+|[\w-]+)/?([^\s]*)", re.IGNORECASE)
PINTEREST_REGEX = re.compile(r"(https?://)?(?:[a-zA-Z0-9-]+\.)?(pinterest\.(?:com|co\.uk|ru|fr|de|it|es|ca|com\.au)/pin/\d+|pin\.it/[\w-]+)/?([^\s]*)", re.IGNORECASE)
GENERIC_URL_REGEX = re.compile(r"https?://(?:www\.)?[-a-zA-Z0-9@:%._+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}(?:[-a-zA-Z0-9()@:%_+.~#?&/=]*)", re.IGNORECASE)

class PlatformDetector:
    @classmethod
    def extract_first_url(cls, text: str) -> Optional[str]:
        if not text:
            return None
        match = GENERIC_URL_REGEX.search(text)
        return match.group(0).strip() if match else None

    @classmethod
    def detect_platform(cls, url: str) -> Tuple[Platform, Optional[str]]:
        if not url:
            return Platform.UNKNOWN, None
        url_clean = url.strip()
        if not url_clean.startswith(("http://", "https://")):
            url_clean = "https://" + url_clean
        if YOUTUBE_REGEX.search(url_clean):
            return Platform.YOUTUBE, url_clean
        if INSTAGRAM_REGEX.search(url_clean):
            return Platform.INSTAGRAM, url_clean
        if TIKTOK_REGEX.search(url_clean):
            return Platform.TIKTOK, url_clean
        if PINTEREST_REGEX.search(url_clean):
            return Platform.PINTEREST, url_clean
        return Platform.UNKNOWN, None
