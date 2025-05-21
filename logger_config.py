"""
logger_config.py
================
Configuration of logger.
"""
import logging
import coloredlogs

def setup_logger() -> logging:
    """Configure logging system"""
    # Set PIL log to warning level
    logging.getLogger("PIL").setLevel(logging.WARNING)

    logger = logging.getLogger('flowrensics')
    logger.setLevel(logging.INFO)
    logger.propagate = False

    # Delete all handlers
    if logger.hasHandlers():
        logger.handlers.clear()

    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')

    # File handler
    file_handler = logging.FileHandler('flowrensics.log', mode='a', encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Console handler
    coloredlogs.install(level='INFO', logger=logger, fmt='%(asctime)s [%(levelname)s] %(message)s')

    return logger
