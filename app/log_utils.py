# log.py
import logging
from logging.handlers import TimedRotatingFileHandler

def get_daily_logger():
    logger = logging.getLogger("microdom-task")
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        handler = TimedRotatingFileHandler(
            "/app/logs/microdom.log",
            when="midnight",
            interval=1,
            backupCount=7,
            encoding="utf-8"
        )
        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger