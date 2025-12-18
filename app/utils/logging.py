import inspect
import logging
import sys

from loguru import logger


class InterceptHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        # Get corresponding Loguru level if it exists.
        try:
            level: str | int = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message.
        frame, depth = inspect.currentframe(), 0
        while frame:
            filename = frame.f_code.co_filename
            is_logging = filename == logging.__file__
            is_frozen = "importlib" in filename and "_bootstrap" in filename
            if depth > 0 and not (is_logging or is_frozen):
                break
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def setup_logging(filename: str) -> None:
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    logger.remove()
    logger.add(sys.stderr, level="INFO", backtrace=True, diagnose=True, enqueue=True)
    logger.add(
        f"logs/{filename}",
        rotation="50 MB",
        compression="zip",
        level="DEBUG",
        backtrace=True,
        diagnose=True,
        enqueue=True,
    )
