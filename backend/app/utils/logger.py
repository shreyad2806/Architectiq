from loguru import logger
import sys

logger.remove()

logger.add(sys.stdout)

logger.info("Logger initialized")
