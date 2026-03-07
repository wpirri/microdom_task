import asyncio
import httpx
from app.log_utils import get_daily_logger
from app.config_utils import get_config_value
from app.mysql_utils import mysql_execute, mysql_query

logger = get_daily_logger()

async def run_task():
    logger.info("Running scheduled task...")


async def worker_loop():
    while True:
        await run_task()
        await asyncio.sleep(get_config_value("TASK_INTERVAL", 15))
        