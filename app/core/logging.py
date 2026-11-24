import logging
import structlog
from app.core.config import settings

def configure_logging():
    logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
    structlog.configure(processors=[structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level, structlog.processors.JSONRenderer()],
        logger_factory=structlog.stdlib.LoggerFactory())

logger = structlog.get_logger()
