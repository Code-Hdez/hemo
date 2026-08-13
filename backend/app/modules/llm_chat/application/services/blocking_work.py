from __future__ import annotations

import asyncio
from collections.abc import Callable
from functools import partial
from typing import TypeVar


T = TypeVar("T")


class BoundedBlockingExecutor:
    """Run synchronous CPU/library work away from the event loop with backpressure.

    ``asyncio.to_thread`` alone uses the process-wide executor and does not bound the
    amount of work submitted by this module.  The semaphore is deliberately held
    until the underlying thread finishes, even when the awaiting request is
    cancelled, so cancellation cannot create hidden FastEmbed/BM25 concurrency.
    """

    def __init__(self, *, max_concurrency: int = 2) -> None:
        if max_concurrency < 1:
            raise ValueError("max_concurrency must be positive")
        self.max_concurrency = max_concurrency
        self._slots = asyncio.Semaphore(max_concurrency)

    async def run(
        self,
        function: Callable[..., T],
        /,
        *args: object,
        **kwargs: object,
    ) -> T:
        await self._slots.acquire()
        task = asyncio.create_task(
            asyncio.to_thread(partial(function, *args, **kwargs))
        )
        try:
            result = await asyncio.shield(task)
        except asyncio.CancelledError:
            # Shielding prevents cancellation of the Future that represents the
            # running thread. Release capacity only when that real work completes.
            task.add_done_callback(lambda _task: self._slots.release())
            raise
        except BaseException:
            self._slots.release()
            raise
        self._slots.release()
        return result
