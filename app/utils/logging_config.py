from loguru import logger
import sys
import os
from config.settings import settings


def setup_logging():
    """Configure Loguru for HIPAA-compliant logging"""

    # Remove default handler
    logger.remove()

    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)

    # Console logging (for development)
    if settings.debug:
        logger.add(
            sys.stdout,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            level=settings.log_level,
            colorize=True,
        )

    # File logging (HIPAA compliant - no PII)
    logger.add(
        settings.log_file,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level=settings.log_level,
        rotation="100 MB",
        retention="30 days",
        compression="zip",
        serialize=False,
        enqueue=True,  # Thread-safe logging
        backtrace=True,
        diagnose=False,  # Don't include variable values for HIPAA compliance
    )

    # Audit logging for HIPAA compliance
    if settings.audit_logging:
        logger.add(
            "./logs/audit.log",
            format="{time:YYYY-MM-DD HH:mm:ss} | AUDIT | {extra[user_id]} | {extra[action]} | {extra[resource]} | {message}",
            level="INFO",
            rotation="50 MB",
            retention="7 years",  # HIPAA requirement
            compression="zip",
            filter=lambda record: "audit" in record["extra"],
        )

    logger.info("Logging configuration initialized")
