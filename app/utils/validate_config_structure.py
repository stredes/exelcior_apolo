# app/utils/validate_config_structure.py
from __future__ import annotations
from typing import Any, Dict, Tuple

_MODE_LIST_KEYS = (
    "eliminar",
    "sumar",
    "mantener_formato",
    "formato_texto",
    "conservar",
    "nombre_archivo_digitos",  # soportado si aparece
)
_MODE_INT_KEYS = ("start_row", "vista_previa_fuente")

def _as_list(x: Any) -> list:
    if x is None:
        return []
    if isinstance(x, list):
        return x
    # permite valores sueltos (str, int, etc.) y los mete en lista
    return [x]

def _sanitize_mode_rules(rules_in: Any) -> Dict[str, Any]:
    """Normaliza y valida un bloque de reglas de un modo."""
    rules = dict(rules_in) if isinstance(rules_in, dict) else {}

    # Listas
    for k in _MODE_LIST_KEYS:
        vals = _as_list(rules.get(k, []))
        # Normaliza a str salvo nombre_archivo_digitos que puede traer ints
        if k == "nombre_archivo_digitos":
            # permite ints o strs
            vals = [int(v) if str(v).isdigit() else v for v in vals]
        else:
            vals = [str(v) for v in vals if v is not None]
        rules[k] = vals

    # Wildcard: si aparece "*" en eliminar, lo dejamos como ["*"] (sin duplicados)
    if "*" in rules["eliminar"]:
        rules["eliminar"] = ["*"]

    # Enteros
    for k in _MODE_INT_KEYS:
        try:
            rules[k] = int(rules.get(k, 0) or 0)
        except Exception:
            rules[k] = 0

    return rules

def _validate_v2(cfg_in: Dict[str, Any]) -> Dict[str, Any] | bool:
    """Valida/normaliza esquema v2 (version/paths/modes). Devuelve dict normalizado o False."""
    cfg = dict(cfg_in)

    # version
    ver = cfg.get("version", 2)
    try:
        ver = int(ver)
    except Exception:
        ver = 2
    cfg["version"] = ver
    if ver != 2:
        return False

    # paths: debe ser dict (puede ir vacío; el manager rellena por defecto)
    paths = cfg.get("paths", {})
    if not isinstance(paths, dict):
        paths = {}
    cfg["paths"] = paths

    # modes: requerido
    modes_in = cfg.get("modes")
    if not isinstance(modes_in, dict):
        return False

    modes_out: Dict[str, Any] = {}
    for mode_name, rules in modes_in.items():
        modes_out[str(mode_name)] = _sanitize_mode_rules(rules)

    cfg["modes"] = modes_out
    return cfg

def _validate_v1(cfg_in: Dict[str, Any]) -> Dict[str, Any] | bool:
    """
    Valida/normaliza esquema v1 (modos en top-level).
    Lo envuelve a v2 para facilitar migración del manager.
    """
    if not isinstance(cfg_in, dict):
        return False

    # Detecta si parece v1 (tiene claves de modos conocidas en top-level)
    possible_modes = ("fedex", "urbano", "listados")
    has_any = any(isinstance(cfg_in.get(m), dict) for m in possible_modes)
    if not has_any:
        # No parece v1; no lo tratamos como válido
        return False

    v2: Dict[str, Any] = {"version": 2, "paths": {}, "modes": {}}
    for m in possible_modes:
        if isinstance(cfg_in.get(m), dict):
            v2["modes"][m] = _sanitize_mode_rules(cfg_in[m])

    # Permite además que existan otros modos dinámicos en v1
    for k, v in cfg_in.items():
        if k in ("version", "paths"):  # ignora claves reservadas erróneas en v1
            continue
        if isinstance(v, dict) and k not in v2["modes"]:
            v2["modes"][k] = _sanitize_mode_rules(v)

    return v2

def validate_config_structure(cfg: Any) -> Dict[str, Any] | Tuple[Dict[str, Any]] | bool:
    """
    Contrato usado por config_manager:
      - Si retorna dict -> se usa ese dict normalizado.
      - Si retorna (dict,) -> también se acepta (compat).
      - Si retorna True/False -> el manager decide (no bloqueante).
    """
    if not isinstance(cfg, dict):
        return False

    # v2 preferente
    if cfg.get("version") == 2 or "modes" in cfg:
        v2 = _validate_v2(cfg)
        if isinstance(v2, dict):
            return v2
        # si falló v2, intentamos v1 como fallback
        v1 = _validate_v1(cfg)
        if isinstance(v1, dict):
            return v1
        return False

    # v1
    v1 = _validate_v1(cfg)
    if isinstance(v1, dict):
        return v1

    return False
