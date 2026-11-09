import time
import uuid
from dataclasses import dataclass
from typing import Dict, Optional
from bot.services.downloader.base import VideoMetadata

@dataclass
class PendingRequest:
    req_id: str
    user_id: int
    url: str
    platform: str
    metadata: VideoMetadata
    created_at: float = 0.0

class RequestStore:
    def __init__(self, ttl_seconds: float = 600.0):
        self.ttl_seconds = ttl_seconds
        self._store: Dict[str, PendingRequest] = {}

    def save(self, user_id: int, url: str, platform: str, metadata: VideoMetadata) -> str:
        req_id = uuid.uuid4().hex[:10]
        self._store[req_id] = PendingRequest(req_id=req_id, user_id=user_id, url=url, platform=platform, metadata=metadata, created_at=time.time())
        return req_id

    def get(self, req_id: str) -> Optional[PendingRequest]:
        req = self._store.get(req_id)
        if not req or (time.time() - req.created_at) > self.ttl_seconds:
            self._store.pop(req_id, None)
            return None
        return req

    def delete(self, req_id: str) -> None:
        self._store.pop(req_id, None)

request_store = RequestStore()
