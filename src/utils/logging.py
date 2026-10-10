from __future__ import annotations

import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path


def configure_logging(level: int = logging.INFO, log_dir: str | Path = "logs") -> None:
    directory = Path(log_dir)
    directory.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger()
    root.setLevel(level)
    if root.handlers:
        return
    formatter = logging.Formatter("%(asctime)sZ %(levelname)s %(name)s: %(message)s")
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    file_handler = TimedRotatingFileHandler(directory / "bot.log", when="midnight", backupCount=14, utc=True)
    file_handler.setFormatter(formatter)
    root.addHandler(console)
    root.addHandler(file_handler)
