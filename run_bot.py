import asyncio
import logging

from app.integrations.telegram_bot import run_bot

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)

if __name__ == "__main__":
    asyncio.run(run_bot())
