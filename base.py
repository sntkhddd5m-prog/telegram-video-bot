from dataclasses import dataclass, field
from typing import List, Optional
from abc import ABC, abstractmethod

class DownloadError(Exception): pass
class VideoUnavailableError(DownloadError): pass
class FileSizeExceededError(DownloadError):
    def __init__(self, size_mb: float, max_mb: float = 50.0):
        super().__init__(f"File size {size_mb:.1f} MB exceeds maximum {max_mb} MB")
        self.size_mb = size_mb

class PlatformRateLimitError(DownloadError): pass
class DrmProtectedError(DownloadError): pass
class DownloadTimeoutError(DownloadError): pass
class NotAVideoError(DownloadError): pass

@dataclass
class VideoMetadata:
    title: str
    platform: str
    url: str
    duration_seconds: int = 0
    duration_str: str = "00:00"
    thumbnail_url: Optional[str] = None
    available_qualities: List[str] = field(default_factory=lambda: ["360p", "720p", "1080p", "best"])
    is_video: bool = True

@dataclass
class DownloadResult:
    file_path: str
    file_size_bytes: int
    file_size_mb: float
    title: str
    platform: str
    quality: str
    duration_seconds: int = 0
    width: Optional[int] = None
    height: Optional[int] = None

class BaseDownloader(ABC):
    @abstractmethod
    async def extract_info(self, url: str) -> VideoMetadata: pass
    @abstractmethod
    async def download(self, url: str, output_dir: str, quality: str = "best") -> DownloadResult: pass
