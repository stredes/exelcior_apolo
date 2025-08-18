# app/config/config_manager.py
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Tuple, Optional

from app.utils.validate_config_structure import validate_config_structure
from app.core.logger_eventos import log_evento

# -----------------------------------------------------------------------------
# Rutas y prioridad
# -----------------------------------------------------------------------------
APP_HOME = Path.home() / ".exelcior_apolo"
APP_HOME.mkdir(parents=True, exist_ok=True)

ENV_CFG = os.environ.get("EXCELPRINTER_CONFIG", "").strip()
USER_CFG_PATH = APP_HOME / "config.json"
DEFAULT_CFG_PATH = Path("app/config/excel_printer_default.json")

# Contenido mínimo por si el default se borra accidentalmente
_MINIMAL_DEFAULT = {
    "version": 1,
    "listados": {"start_row": 0, "eliminar": [], "sumar": [], "mantener_formato": [], "formato_texto": []}
}


# -----------------------------------------------------------------------------
# Utilidades internas
# -----------------------------------------------------------------------------
def _read_json(path: Path) -> Dict[str, Any]:
    try:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        log_evento(f"❌ Error leyendo JSON en {path}: {e}", "error")
        return {}


def _write_json_atomic(path: Path, data: Dict[str, Any]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def _deep_merge(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(a)
    for k, v in b.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def get_config_paths() -> Tuple[Optional[Path], Path, Path]:
    env_path = Path(ENV_CFG) if ENV_CFG else None
    return env_path, USER_CFG_PATH, DEFAULT_CFG_PATH


def _validate_and_log(cfg: Dict[str, Any], origin: str) -> Dict[str, Any]:
    try:
        validated = validate_config_structure(cfg)
        log_evento(f"✅ Config validada desde {origin}", "info")
        return validated
    except Exception as e:
        log_evento(f"⚠️ Config no válida ({origin}): {e}. Se usará tal cual.", "warning")
        return cfg


# -----------------------------------------------------------------------------
# Bootstrap & reparación
# -----------------------------------------------------------------------------
def ensure_defaults() -> None:
    """
    Garantiza que exista el archivo de defaults. Si no existe, lo crea con _MINIMAL_DEFAULT.
    """
    try:
        DEFAULT_CFG_PATH.parent.mkdir(parents=True, exist_ok=True)
        if not DEFAULT_CFG_PATH.exists():
            _write_json_atomic(DEFAULT_CFG_PATH, _MINIMAL_DEFAULT)
            log_evento(f"🧩 Default creado: {DEFAULT_CFG_PATH}", "warning")
    except Exception as e:
        log_evento(f"❌ No se pudo crear default en {DEFAULT_CFG_PATH}: {e}", "error")


def repair_user_config() -> None:
    """
    Repara el user config agregando claves faltantes desde default.
    No elimina claves extra; solo completa ausentes.
    """
    ensure_defaults()
    default_cfg = _read_json(DEFAULT_CFG_PATH)
    user_cfg = _read_json(USER_CFG_PATH)
    if not user_cfg:
        # Nada que reparar
        return

    # Completar claves por modo presentes en default
    repaired = _deep_merge(default_cfg, user_cfg)  # user sobrescribe, pero se asegura base
    if repaired != user_cfg:
        try:
            _write_json_atomic(USER_CFG_PATH, repaired)
            log_evento("🛠️ User config reparado con claves faltantes desde default.", "info")
        except Exception as e:
            log_evento(f"❌ Error reparando user config: {e}", "error")


def restore_user_config_from_defaults() -> None:
    """
    Restaura completamente el user config desde el default (sobrescribe).
    Útil cuando se borró la config del usuario o quedó corrupta.
    """
    ensure_defaults()
    default_cfg = _read_json(DEFAULT_CFG_PATH) or _MINIMAL_DEFAULT
    try:
        _write_json_atomic(USER_CFG_PATH, default_cfg)
        log_evento(f"🔄 User config restaurado desde default en {USER_CFG_PATH}", "warning")
    except Exception as e:
        log_evento(f"❌ Error restaurando user config: {e}", "error")


# -----------------------------------------------------------------------------
# API pública
# -----------------------------------------------------------------------------
def load_config() -> Dict[str, Any]:
    """
    Carga la configuración efectiva:
      - Si EXCELPRINTER_CONFIG está definida -> usa solo ese archivo.
      - Si no: merge DEFAULT + USER (USER sobreescribe).
    Si faltan archivos, se auto-crean/reparan.
    """
    ensure_defaults()

    env_path, user_path, default_path = get_config_paths()

    if env_path:
        cfg_env = _read_json(env_path)
        cfg_env = _validate_and_log(cfg_env, f"ENV:{env_path}")
        log_evento(f"[CONFIG] origen=ENV ({env_path})", "info")
        return cfg_env

    cfg_default = _validate_and_log(_read_json(default_path) or _MINIMAL_DEFAULT, f"default:{default_path}")
    cfg_user = _read_json(user_path)

    if not cfg_user:
        # Si no hay user config, escribe una copia del default para que el usuario la pueda editar
        try:
            _write_json_atomic(user_path, cfg_default)
            log_evento(f"📝 User config inicializado desde default: {user_path}", "info")
            cfg_user = _read_json(user_path)
        except Exception as e:
            log_evento(f"❌ No se pudo inicializar user config: {e}", "error")
            cfg_user = {}

    # Repara el user config si faltan claves (completa desde default)
    repair_user_config()
    cfg_user = _read_json(user_path)

    cfg = _deep_merge(cfg_default, cfg_user)
    log_evento(f"[CONFIG] default={default_path} + user={user_path} -> aplicado", "info")
    return cfg


def save_config(config: Dict[str, Any]) -> bool:
    """
    Guarda la configuración del usuario en USER_CFG_PATH.
    """
    def convert_sets(obj):
        if isinstance(obj, set):
            return list(obj)
        if isinstance(obj, dict):
            return {k: convert_sets(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [convert_sets(i) for i in obj]
        return obj

    try:
        APP_HOME.mkdir(parents=True, exist_ok=True)
        cleaned = convert_sets(config)
        _write_json_atomic(USER_CFG_PATH, cleaned)
        log_evento(f"💾 Config guardada en {USER_CFG_PATH}", "info")
        return True
    except Exception as e:
        log_evento(f"❌ Error al guardar configuración en {USER_CFG_PATH}: {e}", "error")
        return False


def guardar_ultimo_path(path_str: str, clave: str = "ultimo_archivo_excel") -> None:
    cfg = load_config()
    cfg[clave] = str(path_str)
    if save_config(cfg):
        log_evento(f"📍 Ruta actualizada en configuración: {clave} = {path_str}", "info")


def _norm_mode(mode: Optional[str]) -> str:
    return (mode or "").strip().lower()


def get_effective_mode_rules(mode: str, cfg: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    cfg = cfg or load_config()
    m = _norm_mode(mode)
    rules = cfg.get(m, {}) if isinstance(cfg, dict) else {}
    out = {
        "start_row": int(rules.get("start_row", 0) or 0),
        "eliminar": list(rules.get("eliminar", []) or []),
        "sumar": list(rules.get("sumar", []) or []),
        "mantener_formato": list(rules.get("mantener_formato", []) or []),
        "formato_texto": list(rules.get("formato_texto", []) or []),
    }
    log_evento(f"[CONFIG] Reglas efectivas para '{m}': {out}", "info")
    return out


def get_start_row(mode: str, cfg: Optional[Dict[str, Any]] = None) -> int:
    return get_effective_mode_rules(mode, cfg).get("start_row", 0)
