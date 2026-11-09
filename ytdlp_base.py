import asyncio
import os
import glob
from typing import Any, Dict, List, Optional
from config.settings import settings
from bot.services.downloader.base import *

def format_duration(seconds: Optional[int]) -> str:
    if seconds is None or seconds < 0: return "N/A"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"

def map_ytdlp_error(error_message: str) -> Exception:
    msg = error_message.lower()
    if any(k in msg for k in ["private", "unavailable"]): return VideoUnavailableError()
    if any(k in msg for k in ["login", "bot", "429"]): return PlatformRateLimitError()
    if "drm" in msg: return DrmProtectedError()
    return DownloadError(error_message)

class YtDlpDownloader(BaseDownloader):
    def __init__(self, platform_name: str = "Generic"):
        self.platform_name = platform_name

    def _get_base_opts(self) -> Dict[str, Any]:
        return {"quiet": True, "no_warnings": True, "socket_timeout": 30, "nocheckcertificate": True, "noplaylist": True}

    def _get_format_spec(self, quality: str) -> str:
        q = quality.lower().strip()
        if q == "360p": return "bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/best[height<=360]/worst"
        if q == "720p": return "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720]/best"
        if q == "1080p": return "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080]/best"
        return "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best"

    def _sync_extract_info(self, url: str) -> VideoMetadata:
        import yt_dlp
        with yt_dlp.YoutubeDL(self._get_base_opts()) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info: raise VideoUnavailableError()
            if "entries" in info and info["entries"]: info = info["entries"][0]
            return VideoMetadata(
                title=info.get("title", "Video"),
                platform=self.platform_name,
                url=url,
                duration_seconds=int(info.get("duration", 0) or 0),
                duration_str=format_duration(info.get("duration")),
            )

    def _sync_download(self, url: str, output_dir: str, quality: str) -> DownloadResult:
        import yt_dlp
        outtmpl = os.path.join(output_dir, "%(title).60s_%(id)s.%(ext)s")
        opts = self._get_base_opts()
        opts.update({
            "format": self._get_format_spec(quality),
            "outtmpl": outtmpl,
            "merge_output_format": "mp4",
        })
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if "entries" in info and info["entries"]: info = info["entries"][0]
            files = [f for f in glob.glob(os.path.join(output_dir, "*")) if not f.endswith((".part", ".ytdl")) and os.path.isfile(f)]
            if not files: raise DownloadError("File not found")
            file_path = files[0]
            size_bytes = os.path.getsize(file_path)
            size_mb = size_bytes / (1024 * 1024)
            if size_mb > settings.MAX_FILE_SIZE_MB:
                raise FileSizeExceededError(size_mb, float(settings.MAX_FILE_SIZE_MB))
            return DownloadResult(
                file_path=file_path, file_size_bytes=size_bytes, file_size_mb=size_mb,
                title=info.get("title", "Video"), platform=self.platform_name, quality=quality,
                duration_seconds=int(info.get("duration", 0) or 0)
            )

    async def extract_info(self, url: str) -> VideoMetadata:
        return await asyncio.to_thread(self._sync_extract_info, url)

    async def download(self, url: str, output_dir: str, quality: str = "best") -> DownloadResult:
        return await asyncio.to_thread(self._sync_download, url, output_dir, quality)
