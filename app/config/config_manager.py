# app/config/config_manager.py
from __future__ import annotations

import json
import os
import platform
from pathlib import Path
from typing import Any, Dict, Tuple, Optional, Union

from app.utils.validate_config_structure import validate_config_structure
from app.core.logger_eventos import log_evento

# =============================================================================
# Ubicaciones de config y nombres estándar
# =============================================================================
APP_HOME = Path.home() / ".exelcior_apolo"
APP_HOME.mkdir(parents=True, exist_ok=True)

# Variables de entorno:
# - EXCELPRINTER_CONFIG: puede apuntar a un archivo JSON específico o a una carpeta
# - EXCELPRINTER_CONFIG_DIR: apunta a una carpeta que contiene el JSON
ENV_CFG = os.environ.get("EXCELPRINTER_CONFIG", "").strip()
ENV_CFG_DIR = os.environ.get("EXCELPRINTER_CONFIG_DIR", "").strip()

# Nombre preferido del archivo de usuario y nombres legacy soportados
_PREFERRED_USER_FILE = "excel_print_config.json"  # requerido por usuario
_LEGACY_USER_FILES = ["excel_printer_config.json", "config.json"]

# Ruta ABSOLUTA al default que vive en el paquete (exportada para otros módulos)
DEFAULT_CFG_PATH = Path(__file__).resolve().parent / "excel_printer_default.json"

# =============================================================================
# Defaults v2 (paths + modes)
# =============================================================================
def _detect_default_downloads_dir() -> str:
    cand = Path.home() / "Downloads"
    return str(cand) if cand.exists() else str(Path.home())

def _detect_default_output_dir() -> str:
    out = APP_HOME / "output"
    out.mkdir(parents=True, exist_ok=True)
    return str(out)

def _detect_default_libreoffice_program_dir() -> str:
    if platform.system() == "Windows":
        # Común en instalaciones estándar; el usuario puede ajustarlo
        return r"C:\Program Files\LibreOffice\program"
    return ""  # En Linux/macOS normalmente no hace falta

_MINIMAL_DEFAULT_V2: Dict[str, Any] = {
    "version": 2,
    "paths": {
        "downloads_dir": _detect_default_downloads_dir(),
        "output_dir": _detect_default_output_dir(),
        "last_opened_file": "",
        "libreoffice_program_dir": _detect_default_libreoffice_program_dir(),
        "default_printer": "",
        "excel_com_enabled": True,  # relevante en Windows
    },
    "modes": {
        "listados": {
            "eliminar": ["Vendedor", "Total", "Nº", "Moneda", "Tipo cambio", "Tipo doc", "RUT", "Glosa"],
            "sumar": [],
            "mantener_formato": [],
            "formato_texto": [],
            "conservar": [],                  # <-- soportado
            "start_row": 0,
            "vista_previa_fuente": 10
        },
        "fedex": {
            # Por defecto eliminamos columnas de ruido comunes; el usuario puede sobreescribir
            "eliminar": [
                "returnTrackingId","senderAccountNumber","recipientState","quoteId","creationDate",
                "departmentNumber","totalShipmentWeight","recipientPhoneExtension","poNumber","paymentType",
                "recipientEmail","etdEnabled","senderResidential","packageWeight","senderCompany",
                "recipientResidential","recipientTin","recipientCountry","recipientLine1","height",
                "estimatedShippingCosts","length","recipientContactNumber","senderCountry","returnRmaNumber",
                "senderLine1","width","senderPhoneExtension","errors","senderLine3","senderState","senderTin",
                "invoiceNumber","senderLine2","senderEmail","senderContactName","senderCity","pickupId",
                "shipmentType","returnReason","senderPostcode","status","senderContactNumber","weightUnits",
                "recipientLine2","recipientPostcode"
            ],
            "sumar": ["numberOfPackages"],    # NO sumar IDs
            "mantener_formato": ["masterTrackingNumber", "pieceTrackingNumber", "trackingNumber"],
            "formato_texto": [],
            "conservar": [],                  # <-- soportado (e.g. si el user usa eliminar="*" + conservar=[...])
            "start_row": 0,
            "vista_previa_fuente": 10
        },
        "urbano": {
            "eliminar": ["AGENCIA","SHIPPER","FECHA CHK","DIAS","ESTADO","SERVICIO","PESO"],
            "sumar": ["PIEZAS"],
            "mantener_formato": [],
            "formato_texto": [],
            "conservar": [],                  # <-- soportado
            "start_row": 2,
            "vista_previa_fuente": 10
        }
    }
}

# =============================================================================
# Utilidades JSON (lectura/escritura segura)
# =============================================================================
def _read_json(path: Optional[Path]) -> Dict[str, Any]:
    try:
        if not path or not path.exists():
            return {}
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            log_evento(f"⚠️ JSON top-level no es dict en {path}. Se ignora.", "warning")
            return {}
        return data
    except Exception as e:
        log_evento(f"❌ Error leyendo JSON en {path}: {e}", "error")
        return {}

def _write_json_atomic(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)

def _ensure_dict(obj: Any, fallback: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return obj if isinstance(obj, dict) else ({} if fallback is None else dict(fallback))

def _deep_merge(a: Any, b: Any) -> Dict[str, Any]:
    """Merge profundo: dict a <- dict b (b sobrescribe a)."""
    a = _ensure_dict(a)
    b = _ensure_dict(b)
    out: Dict[str, Any] = dict(a)
    for k, v in b.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out

# =============================================================================
# Defaults en disco
# =============================================================================
def ensure_defaults() -> None:
    """Garantiza que exista el default v2 del paquete; si no, crea uno mínimo."""
    try:
        DEFAULT_CFG_PATH.parent.mkdir(parents=True, exist_ok=True)
        if not DEFAULT_CFG_PATH.exists():
            _write_json_atomic(DEFAULT_CFG_PATH, _MINIMAL_DEFAULT_V2)
            log_evento(f"🧩 Default v2 creado: {DEFAULT_CFG_PATH}", "warning")
    except Exception as e:
        log_evento(f"❌ No se pudo crear default en {DEFAULT_CFG_PATH}: {e}", "error")

# =============================================================================
# Resolución de ruta de config de usuario
# =============================================================================
def _resolve_user_cfg_path() -> Path:
    """
    Devuelve la RUTA ACTIVA del archivo de configuración del usuario.
    Prioridad:
      1) EXCELPRINTER_CONFIG -> si es archivo, úsalo; si es carpeta, <carpeta>/_PREFERRED_USER_FILE
      2) EXCELPRINTER_CONFIG_DIR -> <carpeta>/_PREFERRED_USER_FILE
      3) ~/.exelcior_apolo/ -> si existe algún legacy, úsalo; si no, crea el preferido.
    """
    # 1) EXCELPRINTER_CONFIG (archivo o carpeta)
    if ENV_CFG:
        p = Path(ENV_CFG)
        if p.is_dir():
            return p / _PREFERRED_USER_FILE
        if p.suffix:
            return p
        # si no es dir y no tiene sufijo, trátalo como carpeta
        return p / _PREFERRED_USER_FILE

    # 2) EXCELPRINTER_CONFIG_DIR (carpeta)
    if ENV_CFG_DIR:
        return Path(ENV_CFG_DIR) / _PREFERRED_USER_FILE

    # 3) Carpeta HOME: elegir existente (preferido o legacy); si nada existe, preferido
    candidates = [APP_HOME / _PREFERRED_USER_FILE] + [APP_HOME / n for n in _LEGACY_USER_FILES]
    for c in candidates:
        if c.exists():
            return c
    return candidates[0]  # crea preferido si no existe nada

def get_config_paths() -> Tuple[Optional[Path], Path, Path]:
    """
    Retorna (env_path, user_path, default_path)

    - Si EXCELPRINTER_CONFIG apunta a archivo => env_path = ese archivo (máxima prioridad)
    - Si EXCELPRINTER_CONFIG apunta a carpeta => env_path = carpeta/_PREFERRED_USER_FILE  (también con prioridad)
    - Si EXCELPRINTER_CONFIG no está => env_path = None
    - user_path = ruta activa resuelta (_resolve_user_cfg_path)
    """
    env_path: Optional[Path] = None

    if ENV_CFG:
        p = Path(ENV_CFG)
        if p.is_dir():
            env_path = p / _PREFERRED_USER_FILE
        elif p.suffix:
            env_path = p
        else:
            env_path = p / _PREFERRED_USER_FILE

    user_cfg_path = _resolve_user_cfg_path()
    return env_path, user_cfg_path, DEFAULT_CFG_PATH

# =============================================================================
# Migración: v1 (modos en top-level) → v2 (paths + modes)
# =============================================================================
def _migrate_to_v2(cfg: Dict[str, Any]) -> Dict[str, Any]:
    """
    Acepta esquemas antiguos v1 (claves 'fedex','urbano','listados' en top-level)
    y los lleva a {"version":2, "paths":{...}, "modes":{...}}. No escribe a disco.
    """
    if not cfg:
        return dict(_MINIMAL_DEFAULT_V2)

    if cfg.get("version") == 2 and isinstance(cfg.get("modes"), dict):
        return cfg  # ya v2

    v2 = dict(_MINIMAL_DEFAULT_V2)

    # Arrastrar pistas útiles del v1
    last_path = cfg.get("ultimo_archivo_excel") or cfg.get("ultimo_path") or cfg.get("last_opened_file") or ""
    if last_path:
        v2["paths"]["last_opened_file"] = last_path

    # Mover posibles modos top-level a modes
    possible_modes = ("fedex", "urbano", "listados")
    for m in possible_modes:
        if isinstance(cfg.get(m), dict):
            v2["modes"][m] = _deep_merge(v2["modes"].get(m, {}), cfg[m])

    # Copiar otras claves globales si existían
    if "default_printer" in cfg:
        v2["paths"]["default_printer"] = cfg.get("default_printer", "")
    if "libreoffice_program_dir" in cfg:
        v2["paths"]["libreoffice_program_dir"] = cfg.get("libreoffice_program_dir", "")
    if "excel_com_enabled" in cfg:
        v2["paths"]["excel_com_enabled"] = bool(cfg.get("excel_com_enabled", True))

    v2["version"] = 2
    log_evento("🔁 Migración v1 → v2 aplicada en memoria.", "info")
    return v2

# =============================================================================
# Validación + Coalescencia por modo
# =============================================================================
def _validate_and_log(cfg: Dict[str, Any], origin: str) -> Dict[str, Any]:
    """
    Valida estructura con validate_config_structure. Acepta dict/tuple/bool.
    Si el validador devuelve False, se conserva cfg y se loguea warning.
    """
    try:
        validated: Union[Dict[str, Any], Tuple[Any, ...], bool, Any] = validate_config_structure(cfg)
        if isinstance(validated, dict):
            log_evento(f"✅ Config validada desde {origin}", "info")
            return validated
        if isinstance(validated, tuple) and validated and isinstance(validated[0], dict):
            log_evento(f"✅ Config validada (tuple) desde {origin}", "info")
            return validated[0]
        if isinstance(validated, bool):
            if validated:
                log_evento(f"ℹ️ Validator OK (bool) desde {origin}; se mantiene cfg.", "info")
            else:
                log_evento(f"⚠️ Validator NOT OK (bool) desde {origin}; se mantiene cfg.", "warning")
            return cfg
        log_evento(f"⚠️ Validator devolvió {type(validated).__name__} desde {origin}; se mantiene cfg.", "warning")
        return cfg
    except Exception as e:
        log_evento(f"⚠️ Error en validate_config_structure ({origin}): {e}. Se usa cfg original.", "warning")
        return cfg

def _coalesce_mode_rules(default_mode: Dict[str, Any], user_mode: Dict[str, Any]) -> Dict[str, Any]:
    """
    Hereda defaults cuando el user deja listas vacías. Garantiza ints válidos.
    Listas: eliminar, sumar, mantener_formato, formato_texto, conservar
    Enteros: start_row, vista_previa_fuente
    """
    d = default_mode or {}
    u = user_mode or {}
    out = dict(d)
    out.update(u)  # user override

    def _use_default_if_empty(key: str):
        if key in out:
            v = out[key]
            if v is None or (isinstance(v, list) and len(v) == 0):
                out[key] = list(d.get(key, []))
        else:
            out[key] = list(d.get(key, []))

    for k in ("eliminar", "sumar", "mantener_formato", "formato_texto", "conservar"):
        _use_default_if_empty(k)

    for k in ("start_row", "vista_previa_fuente"):
        try:
            out[k] = int(out.get(k, d.get(k, 0)))
        except Exception:
            out[k] = int(d.get(k, 0))

    return out

# =============================================================================
# Carga principal
# =============================================================================
def load_config() -> Dict[str, Any]:
    """
    Carga configuración efectiva (v2):
      - Bootstrap defaults v2 en disco si falta.
      - Lee DEFAULT + USER (+ENV si se definió archivo externo).
      - Migra v1→v2 en memoria.
      - Merge profundo: default <- user <- env
      - Valida y coalesce por cada modo.
    """
    ensure_defaults()
    env_path, user_path, default_path = get_config_paths()

    log_evento(f"[CONFIG] DEFAULT: {default_path}", "info")
    log_evento(f"[CONFIG] USER   : {user_path}", "info")
    if env_path:
        log_evento(f"[CONFIG] ENV    : {env_path}", "info")

    default_cfg = _read_json(default_path) or dict(_MINIMAL_DEFAULT_V2)
    user_cfg = _read_json(user_path)
    env_cfg = _read_json(env_path) if env_path else {}

    # Si no hay config de usuario, inicializar con default v2
    if not user_cfg:
        try:
            _write_json_atomic(user_path, default_cfg)
            log_evento(f"📝 User config creado desde default en {user_path}", "info")
            user_cfg = _read_json(user_path)
        except Exception as e:
            log_evento(f"❌ No se pudo crear user config: {e}", "error")
            user_cfg = {}

    # Migración v1→v2 en memoria
    default_cfg = _migrate_to_v2(default_cfg)
    user_cfg = _migrate_to_v2(user_cfg)
    env_cfg = _migrate_to_v2(env_cfg) if env_cfg else {}

    # Merge profundo
    merged = _deep_merge(default_cfg, user_cfg)
    merged = _deep_merge(merged, env_cfg)

    # Validar estructura
    merged = _validate_and_log(merged, "merged")

    # Coalescer por modo (herencia de listas/ints) con soporte a modos dinámicos
    d_modes = _ensure_dict(merged.get("modes", {}))
    out_modes: Dict[str, Any] = {}
    for mode_name, mode_cfg in d_modes.items():
        base_default_mode = _MINIMAL_DEFAULT_V2["modes"].get(mode_name, {})
        out_modes[mode_name] = _coalesce_mode_rules(base_default_mode, mode_cfg)
    merged["modes"] = out_modes

    # paths efectivos (hereda defaults si faltan claves)
    merged["paths"] = _deep_merge(_MINIMAL_DEFAULT_V2["paths"], _ensure_dict(merged.get("paths", {})))

    return merged

# =============================================================================
# API pública
# =============================================================================
def save_config(config: Dict[str, Any]) -> bool:
    """
    Guarda TODO el diccionario de configuración (paths + modes).
    Preferencia de destino:
      - Si EXCELPRINTER_CONFIG (archivo o carpeta) está definido => guarda en ese archivo resuelto (prioridad).
      - Si no, guarda en user_path resuelto (~/.exelcior_apolo/excel_print_config.json).
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
        env_path, user_path, _ = get_config_paths()
        target = env_path if env_path else user_path  # prioridad al ENV resuelto
        cleaned = convert_sets(config)
        _write_json_atomic(target, cleaned)
        log_evento(f"💾 Config guardada en {target}", "info")
        return True
    except Exception as e:
        log_evento(f"❌ Error al guardar configuración: {e}", "error")
        return False

def _norm_mode(mode: Optional[str]) -> str:
    return (mode or "").strip().lower()

def get_effective_mode_rules(mode: str, cfg: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Devuelve reglas efectivas del modo.
    Compatibilidad: si cfg fuera v1 (sin 'modes'), intenta top-level.
    """
    cfg = cfg or load_config()
    m = _norm_mode(mode)

    # v2
    modes = cfg.get("modes", {})
    if isinstance(modes, dict) and m in modes:
        rules = modes[m]
    else:
        # legacy v1
        rules = cfg.get(m, {}) if isinstance(cfg, dict) else {}

    out = {
        "start_row": int(rules.get("start_row", 0) or 0),
        "eliminar": list(rules.get("eliminar", []) or []),
        "sumar": list(rules.get("sumar", []) or []),
        "mantener_formato": list(rules.get("mantener_formato", []) or []),
        "formato_texto": list(rules.get("formato_texto", []) or []),
        "conservar": list(rules.get("conservar", []) or []),  # <-- incluido
        "vista_previa_fuente": int(rules.get("vista_previa_fuente", 10) or 10),
    }
    log_evento(f"[CONFIG] Reglas efectivas para '{m}': {out}", "info")
    return out

def get_start_row(mode: str, cfg: Optional[Dict[str, Any]] = None) -> int:
    return get_effective_mode_rules(mode, cfg).get("start_row", 0)

def get_paths(cfg: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Devuelve bloque 'paths' efectivo (hereda defaults si faltan claves).
    """
    cfg = cfg or load_config()
    return _deep_merge(_MINIMAL_DEFAULT_V2["paths"], _ensure_dict(cfg.get("paths", {})))

def set_paths(cfg: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
    """
    Actualiza en memoria el bloque 'paths'. Luego puedes llamar a save_config(cfg).
    Ejemplos:
      set_paths(cfg, default_printer="HP-01")
      set_paths(cfg, downloads_dir="C:/Users/User/Downloads")
      set_paths(cfg, excel_com_enabled=False)
    """
    cfg.setdefault("paths", {})
    for k, v in kwargs.items():
        cfg["paths"][k] = v
    return cfg

def guardar_ultimo_path(path_str: str, clave: str = "last_opened_file") -> None:
    """
    Guarda la última ruta abierta bajo paths.last_opened_file (v2).
    Además deja sombra legacy 'ultimo_archivo_excel' por compatibilidad.
    """
    cfg = load_config()
    cfg = set_paths(cfg, last_opened_file=str(path_str))
    cfg["ultimo_archivo_excel"] = str(path_str)  # legacy shadow
    save_config(cfg)

def repair_user_config() -> None:
    """
    API mantenida por compatibilidad. La 'reparación' real se hace en load_config()
    mediante migración + merge + coalescencia.
    """
    ensure_defaults()
    log_evento("🛠️ repair_user_config: no-op (gestionado en load_config).", "info")

def restore_user_config_from_defaults() -> None:
    """
    Restaura configuración de usuario a defaults v2 en la ruta activa (ENV si existe, si no ~/.exelcior_apolo).
    """
    ensure_defaults()
    try:
        env_path, user_path, _ = get_config_paths()
        target = env_path if env_path else user_path
        _write_json_atomic(target, _MINIMAL_DEFAULT_V2)
        log_evento(f"🔄 User config restaurado a defaults v2 en {target}", "warning")
    except Exception as e:
        log_evento(f"❌ Error restaurando user config: {e}", "error")
