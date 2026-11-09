import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine, Dict
from config.settings import settings

logger = logging.getLogger(__name__)

@dataclass
class QueueTask:
    task_id: str
    user_id: int
    coro_func: Callable[[], Coroutine[Any, Any, Any]]
    future: asyncio.Future = field(default_factory=asyncio.Future)

class QueueManager:
    def __init__(self, max_concurrent: int = settings.MAX_CONCURRENT_DOWNLOADS, max_queue_size: int = settings.MAX_QUEUE_SIZE, max_per_user: int = settings.USER_MAX_ACTIVE_TASKS):
        self.max_concurrent = max_concurrent
        self.queue: asyncio.Queue[QueueTask] = asyncio.Queue(maxsize=max_queue_size)
        self.active_users: Dict[int, int] = {}
        self.workers: list[asyncio.Task] = []
        self.running: bool = False
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        if self.running:
            return
        self.running = True
        for i in range(self.max_concurrent):
            self.workers.append(asyncio.create_task(self._worker_loop(i)))

    async def stop(self) -> None:
        self.running = False
        for w in self.workers:
            w.cancel()
        await asyncio.gather(*self.workers, return_exceptions=True)
        self.workers.clear()

    async def enqueue(self, task_id: str, user_id: int, coro_func: Callable[[], Coroutine[Any, Any, Any]]) -> asyncio.Future:
        async with self._lock:
            if self.active_users.get(user_id, 0) >= settings.USER_MAX_ACTIVE_TASKS:
                raise ValueError("USER_LIMIT_REACHED")
            self.active_users[user_id] = self.active_users.get(user_id, 0) + 1

        task = QueueTask(task_id=task_id, user_id=user_id, coro_func=coro_func)
        try:
            self.queue.put_nowait(task)
        except asyncio.QueueFull:
            async with self._lock:
                self.active_users[user_id] = max(0, self.active_users.get(user_id, 1) - 1)
            raise ValueError("QUEUE_FULL")
        return task.future

    async def _worker_loop(self, worker_id: int) -> None:
        while self.running:
            try:
                task = await self.queue.get()
            except asyncio.CancelledError:
                break
            try:
                res = await task.coro_func()
                if not task.future.done():
                    task.future.set_result(res)
            except Exception as e:
                if not task.future.done():
                    task.future.set_exception(e)
            finally:
                async with self._lock:
                    cnt = self.active_users.get(task.user_id, 1) - 1
                    if cnt <= 0:
                        self.active_users.pop(task.user_id, None)
                    else:
                        self.active_users[task.user_id] = cnt
                self.queue.task_done()

queue_manager = QueueManager()
