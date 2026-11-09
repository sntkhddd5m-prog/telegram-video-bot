from .ytdlp_base import YtDlpDownloader
class TikTokDownloader(YtDlpDownloader):
    def __init__(self): super().__init__('TikTok')
