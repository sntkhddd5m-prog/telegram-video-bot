from .ytdlp_base import YtDlpDownloader
class YouTubeDownloader(YtDlpDownloader):
    def __init__(self): super().__init__('YouTube')
