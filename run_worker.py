import asyncio

try:
    import uvloop
    uvloop.install()
except ImportError:
    pass

from app.workers.tasks import WorkerSettings
from arq.worker import create_worker


async def main():
    worker = create_worker(WorkerSettings)
    await worker.async_run()


if __name__ == "__main__":
    asyncio.run(main())
