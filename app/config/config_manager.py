# app/config/config_manager.py
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Tuple, Optional, Union

from app.utils.validate_config_structure import validate_config_structure
from app.core.logger_eventos import log_evento

# -----------------------------------------------------------------------------
# Rutas y prioridad
# -----------------------------------------------------------------------------
APP_HOME = Path.home() / ".exelcior_apolo"
APP_HOME.mkdir(parents=True, exist_ok=True)

ENV_CFG = os.environ.get("EXCELPRINTER_CONFIG", "").strip()
USER_CFG_PATH = APP_HOME / "config.json"

# ✅ Ruta ABSOLUTA al default (a prueba de cwd)
DEFAULT_CFG_PATH = Path(__file__).resolve().parent / "excel_printer_default.json"

# -----------------------------------------------------------------------------
# DEFAULT mínimo de respaldo (COMPLETO) por si borran el archivo del repo
# -----------------------------------------------------------------------------
_MINIMAL_DEFAULT: Dict[str, Any] = {
    "version": 1,
    "listados": {
        "eliminar": [
            "Vendedor", "Total", "N\u00ba", "Moneda",
            "Tipo cambio", "Tipo doc", "RUT", "Glosa"
        ],
        "sumar": [],
        "mantener_formato": [],
        "start_row": 0,
        "nombre_archivo_digitos": [],
        "vista_previa_fuente": 10
    },
    "fedex": {
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
        "sumar": ["numberOfPackages", "masterTrackingNumber"],
        "mantener_formato": ["masterTrackingNumber"],
        "start_row": 0,
        "nombre_archivo_digitos": [],
        "vista_previa_fuente": 10
    },
    "urbano": {
        "eliminar": ["AGENCIA","SHIPPER","FECHA CHK","DIAS","ESTADO","SERVICIO","PESO"],
        "sumar": ["PIEZAS"],
        "mantener_formato": [],
        "start_row": 2,
        "nombre_archivo_digitos": [9, 10],
        "vista_previa_fuente": 10
    }
}

# -----------------------------------------------------------------------------
# Utilidades internas
# -----------------------------------------------------------------------------
def _read_json(path: Path) -> Dict[str, Any]:
    try:
        if not path.exists():
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
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def _ensure_dict(obj: Any, fallback: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if isinstance(obj, dict):
        return obj
    return {} if fallback is None else dict(fallback)


def _deep_merge(a: Any, b: Any) -> Dict[str, Any]:
    a = _ensure_dict(a)
    b = _ensure_dict(b)
    out: Dict[str, Any] = dict(a)
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
        validated: Union[Dict[str, Any], Tuple[Any, ...], bool, Any] = validate_config_structure(cfg)
        if isinstance(validated, dict):
            log_evento(f"✅ Config validada desde {origin}", "info")
            return validated
        if isinstance(validated, tuple) and validated and isinstance(validated[0], dict):
            log_evento(f"✅ Config validada (tuple) desde {origin}", "info")
            return validated[0]
        if isinstance(validated, bool):
            if validated:
                log_evento(f"ℹ️ Validator OK (bool) desde {origin}; se mantiene cfg original.", "info")
            else:
                log_evento(f"⚠️ Validator NOT OK (bool) desde {origin}; se mantiene cfg original.", "warning")
            return cfg
        log_evento(f"⚠️ Validator devolvió {type(validated).__name__} desde {origin}; se mantiene cfg original.", "warning")
        return cfg
    except Exception as e:
        log_evento(f"⚠️ Error en validate_config_structure ({origin}): {e}. Se usa cfg original.", "warning")
        return cfg


# --------- Coalesce: hereda default cuando user tiene listas vacías ----------
def _coalesce_mode_rules(default_mode: Dict[str, Any], user_mode: Dict[str, Any]) -> Dict[str, Any]:
    """
    Hereda valores del default cuando en user-mode hay listas vacías o None.
    Para listas: eliminar, sumar, mantener_formato, formato_texto.
    Para ints: start_row, vista_previa_fuente (si inválidos, usa default).
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

    for k in ("eliminar", "sumar", "mantener_formato", "formato_texto"):
        _use_default_if_empty(k)

    for k in ("start_row", "vista_previa_fuente"):
        try:
            out[k] = int(out.get(k, d.get(k, 0)))
        except Exception:
            out[k] = int(d.get(k, 0))

    return out


# -----------------------------------------------------------------------------
# Bootstrap & reparación
# -----------------------------------------------------------------------------
def ensure_defaults() -> None:
    try:
        DEFAULT_CFG_PATH.parent.mkdir(parents=True, exist_ok=True)
        if not DEFAULT_CFG_PATH.exists():
            _write_json_atomic(DEFAULT_CFG_PATH, _MINIMAL_DEFAULT)
            log_evento(f"🧩 Default creado: {DEFAULT_CFG_PATH}", "warning")
    except Exception as e:
        log_evento(f"❌ No se pudo crear default en {DEFAULT_CFG_PATH}: {e}", "error")


def repair_user_config() -> None:
    ensure_defaults()
    default_cfg = _read_json(DEFAULT_CFG_PATH)
    user_cfg = _read_json(USER_CFG_PATH)
    if not user_cfg:
        return
    repaired = _deep_merge(default_cfg, user_cfg)
    if repaired != user_cfg:
        try:
            _write_json_atomic(USER_CFG_PATH, repaired)
            log_evento("🛠️ User config reparado con claves faltantes desde default.", "info")
            _ = _validate_and_log(repaired, "user:repaired")
        except Exception as e:
            log_evento(f"❌ Error reparando user config: {e}", "error")


def restore_user_config_from_defaults() -> None:
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
      - Si EXCELPRINTER_CONFIG está definida -> usa SOLO ese archivo.
      - Si no: merge DEFAULT + USER (USER sobreescribe) + COALESCE (hereda default si user deja listas vacías).
    """
    ensure_defaults()
    env_path, user_path, default_path = get_config_paths()

    if env_path:
        cfg_env = _read_json(env_path)
        cfg_env = _validate_and_log(cfg_env, f"ENV:{env_path}")
        log_evento(f"[CONFIG] origen=ENV ({env_path})", "info")
        return cfg_env

    cfg_default_raw = _read_json(default_path) or _MINIMAL_DEFAULT
    cfg_default = _validate_and_log(cfg_default_raw, f"default:{default_path}")

    cfg_user_raw = _read_json(user_path)
    if not cfg_user_raw:
        try:
            _write_json_atomic(user_path, cfg_default)
            log_evento(f"📝 User config inicializado desde default: {user_path}", "info")
            cfg_user_raw = _read_json(user_path)
        except Exception as e:
            log_evento(f"❌ No se pudo inicializar user config: {e}", "error")
            cfg_user_raw = {}

    repair_user_config()
    cfg_user = _read_json(user_path)

    # Merge final
    cfg = _deep_merge(cfg_default, cfg_user)

    # ✅ Coalesce por modo (si user dejó listas vacías, hereda default)
    for mode in ("listados", "fedex", "urbano"):
        d_mode = (cfg_default or {}).get(mode, {})
        u_mode = (cfg_user or {}).get(mode, {})
        if d_mode or u_mode:
            cfg[mode] = _coalesce_mode_rules(d_mode, u_mode)

    log_evento(f"[CONFIG] default={default_path} + user={user_path} -> aplicado", "info")
    return cfg


def save_config(config: Dict[str, Any]) -> bool:
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
    if not isinstance(cfg, dict) or m not in cfg:
        log_evento(f"[CONFIG] Modo '{m}' no está en la configuración. Usando defaults vacíos.", "warning")
    rules = cfg.get(m, {}) if isinstance(cfg, dict) else {}
    out = {
        "start_row": int(rules.get("start_row", 0) or 0),
        "eliminar": list(rules.get("eliminar", []) or []),
        "sumar": list(rules.get("sumar", []) or []),
        "mantener_formato": list(rules.get("mantener_formato", []) or []),
        "formato_texto": list(rules.get("formato_texto", []) or []),
        "vista_previa_fuente": int(rules.get("vista_previa_fuente", 10) or 10),
    }
    log_evento(f"[CONFIG] Reglas efectivas para '{m}': {out}", "info")
    return out


def get_start_row(mode: str, cfg: Optional[Dict[str, Any]] = None) -> int:
    return get_effective_mode_rules(mode, cfg).get("start_row", 0)
