import logging
from logging.config import dictConfig

def configure_logging():
    log_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(levelname)s: %(name)s: %(message)s"
            },
            "info": {
                "format": "%(levelname)s: %(name)s: %(message)s"
            },
            "error": {
                "format": "%(levelname)s: %(name)s: %(funcName)s: %(message)s"
            }
        },
        "handlers": {
            "default": {
                "formatter": "default",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
            },
            "info": {
                "formatter": "info",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
                "level": "INFO"
            },
            "error": {
                "formatter": "error",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stderr",
                "level": "ERROR"
            }
        },
        "loggers": {
            "uvicorn": {
                "handlers": ["default"],
                "level": "INFO"
            },
            "uvicorn.error": {
                "handlers": ["error"],
                "level": "ERROR"
            },
            "fastapi": {
                "handlers": ["default"],
                "level": "INFO",
                "propagate": False
            },
            "sqlalchemy": {
                "handlers": ["error"],
                "level": "ERROR",
                "propagate": False
            },
            "app": { # Custom logger for our application
                "handlers": ["default", "info", "error"],
                "level": "INFO",
                "propagate": False
            }
        },
        "root": {
            "handlers": ["default"],
            "level": "INFO"
        }
    }
    dictConfig(log_config)
    
    # Example usage:
    # logger = logging.getLogger("app")
    # logger.info("This is an info message")
    # logger.error("This is an error message")
