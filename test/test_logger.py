from pathlib import Path

from app.utils.logger_setup import log_evento


def test_logger_crea_archivo():
    log_evento("Prueba de log desde test", "info")
    archivos = list(Path("logs").glob("*test_logger*.log"))
    assert len(archivos) > 0
