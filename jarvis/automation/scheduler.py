from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable


class Scheduler:
    def __init__(self) -> None:
        self._tasks: set[asyncio.Task[None]] = set()

    def every(self, seconds: float, callback: Callable[[], Awaitable[None]]) -> asyncio.Task[None]:
        async def runner() -> None:
            while True:
                await asyncio.sleep(max(1.0, seconds))
                await callback()
        task = asyncio.create_task(runner())
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return task

    async def stop(self) -> None:
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

