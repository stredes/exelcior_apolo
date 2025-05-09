from pathlib import Path

from app.db import utils_db


def test_config_file_constant():
    assert isinstance(utils_db.CONFIG_FILE, Path)
    assert str(utils_db.CONFIG_FILE).endswith(".json")
