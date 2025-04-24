from app.db import utils_db
from pathlib import Path

def test_config_file_constant():
    assert isinstance(utils_db.CONFIG_FILE, Path)
    assert str(utils_db.CONFIG_FILE).endswith(".json")
