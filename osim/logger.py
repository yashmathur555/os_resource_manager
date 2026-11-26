"""Activity logging. Every module writes to logs/activity.log.

Log line format (parsed by scripts/log_summary.sh, keep in sync):
    2026-01-01 12:00:00 | INFO | osim.scheduler | message
"""
import logging
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(ROOT, "logs")
LOG_FILE = os.path.join(LOG_DIR, "activity.log")

_configured = False


def _configure():
    global _configured
    if _configured:
        return
    os.makedirs(LOG_DIR, exist_ok=True)
    handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    handler.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"))
    root = logging.getLogger("osim")
    root.setLevel(logging.DEBUG)
    root.addHandler(handler)
    root.propagate = False
    _configured = True


def get_logger(module: str) -> logging.Logger:
    _configure()
    return logging.getLogger(f"osim.{module}")
