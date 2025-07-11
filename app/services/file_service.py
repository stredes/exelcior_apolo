import logging
from pathlib import Path
from typing import Tuple
import pandas as pd

from app.core.excel_processor import (
    validate_file as core_validate,
    load_excel,
    apply_transformation
)

# Importación segura de módulos de impresión
from app.printer import (
    printer_fedex,
    printer_urbano,
    printer_listados,
    printer_etiquetas,
    printer_inventario_codigo,
    printer_inventario_ubicacion,
)

logger = logging.getLogger(__name__)


def validate_file(path: str) -> Tuple[bool, str]:
    """Valida que el archivo sea correcto antes de procesar."""
    valid, msg = core_validate(path)
    return valid, msg


def process_file(path_or_df, config_columns, mode: str):
    """
    Carga y transforma un archivo Excel o un DataFrame.
    Retorna: (df original, df transformado)
    """
    if isinstance(path_or_df, pd.DataFrame):
        df = path_or_df
    else:
        df = load_excel(path_or_df, config_columns, mode)
    transformed = apply_transformation(df.copy(), config_columns, mode)
    return df, transformed


# Mapa seguro de funciones de impresión
printer_map = {}

# FEDEx
if hasattr(printer_fedex, "print_fedex"):
    printer_map["fedex"] = printer_fedex.print_fedex
else:
    logger.warning("printer_fedex.print_fedex no está definido")

# URBANO
if hasattr(printer_urbano, "print_urbano"):
    printer_map["urbano"] = printer_urbano.print_urbano
else:
    logger.warning("printer_urbano.print_urbano no está definido")

# LISTADOS
if hasattr(printer_listados, "print_listados"):
    printer_map["listados"] = printer_listados.print_listados
else:
    logger.warning("printer_listados.print_listados no está definido")

# ETIQUETAS
if hasattr(printer_etiquetas, "print_etiquetas"):
    printer_map["etiquetas"] = printer_etiquetas.print_etiquetas
else:
    logger.warning("printer_etiquetas.print_etiquetas no está definido")

# INVENTARIO POR CÓDIGO
if hasattr(printer_inventario_codigo, "print_inventario_codigo"):
    printer_map["inventario_codigo"] = printer_inventario_codigo.print_inventario_codigo
else:
    logger.warning("printer_inventario_codigo.print_inventario_codigo no está definido")

# INVENTARIO POR UBICACIÓN
if hasattr(printer_inventario_ubicacion, "print_inventario_ubicacion"):
    printer_map["inventario_ubicacion"] = printer_inventario_ubicacion.print_inventario_ubicacion
else:
    logger.warning("printer_inventario_ubicacion.print_inventario_ubicacion no está definido")
