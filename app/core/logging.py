import logging
import sys
import structlog
from app.core.config import settings

def setup_logging():
    """
    Set up structured logging using structlog.
    """
    timestamper = structlog.processors.TimeStamper(fmt="iso")
    
    shared_processors = [
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        timestamper,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    if settings.ENVIRONMENT == "production" or not settings.DEBUG:
        processors = shared_processors + [
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]
        log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    else:
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(),
        ]
        log_level = logging.DEBUG

    structlog.configure(
        processors=processors,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    root_logger = logging.getLogger()
    if not root_logger.hasHandlers():
        handler = logging.StreamHandler(sys.stdout)
        # For standard library logs to also be structured:
        # This part can be tricky; ensuring foreign logs are also processed by structlog.
        # A simpler approach for foreign logs might be to just let them use standard formatting
        # or use structlog.stdlib.ProcessorFormatter.wrap_for_formatter.
        # For now, let's keep it simple and focus on structlog for app's own logs.
        # If you want foreign logs (like uvicorn) to be JSON, more setup is needed here for the handler.
        # Example for basic formatting for foreign logs:
        formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)
    
    root_logger.setLevel(log_level)

    logging.getLogger("uvicorn.access").setLevel(logging.WARNING if settings.ENVIRONMENT == "production" else logging.INFO)
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING if settings.ENVIRONMENT == "production" else logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING if not getattr(settings, 'DB_ECHO_LOG', False) else logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("boto3").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)

    logger = structlog.get_logger("app.setup_logging") # Use structlog here
    logger.info(
        "Logging configured",
        environment=settings.ENVIRONMENT,
        log_level=logging.getLevelName(log_level),
        json_logs=settings.ENVIRONMENT == "production" or not settings.DEBUG
    )