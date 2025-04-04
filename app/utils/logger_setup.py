# utils/logger_setup.py
from datetime import datetime
from logging import basicConfig, INFO
from pathlib import Path

def setup_logging():
    LOG_FILE = Path("logs") / f"fallback_log_{datetime.now().strftime('%Y%m%d')}.log"
    LOG_FILE.parent.mkdir(exist_ok=True)

    basicConfig(
        filename=LOG_FILE,
        level=INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        encoding="utf-8"
    )
