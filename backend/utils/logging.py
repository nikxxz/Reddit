import logging
import sys


LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"


def configure_logging(debug: bool = False) -> None:
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format=LOG_FORMAT,
        stream=sys.stdout,
        force=False,
    )
    logging.getLogger("backend").setLevel(level)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
