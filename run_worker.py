import asyncio
import logging

try:
    import uvloop
    uvloop.install()
except ImportError:
    pass

from app.workers.tasks import WorkerSettings
from arq.worker import create_worker

logger = logging.getLogger("arq.worker")


async def main():
    worker = create_worker(WorkerSettings)
    try:
        await worker.async_run()
    except asyncio.CancelledError:
        logger.info("Worker received cancellation, shutting down gracefully")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
