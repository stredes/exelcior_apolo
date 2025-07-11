# tests/printer_map_dry_run.py

import sys
from pathlib import Path
import pandas as pd

# Asegura que se pueda importar app.*
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.services.file_service import printer_map

def generar_df_dummy():
    return pd.DataFrame({
        "Código": ["P001", "P002"],
        "Producto": ["Guantes", "Mascarillas"],
        "Bodega": ["Central", "Sucursal"],
        "Ubicación": ["RE-A-1", "RE-B-2"],
        "N° Serie": ["SN123", "SN456"],
        "Lote": ["L001", "L002"],
        "Fecha Vencimiento": ["2025-12-31", "2026-01-15"],
        "Saldo Stock": [100, 200],
        "RUT": ["12.345.678-9", "98.765.432-1"],
        "Razón Social": ["Clínica X", "Hospital Y"],
        "Dirección": ["Av. Salud 123", "Calle Cura 456"],
        "Comuna": ["Santiago", "Providencia"],
        "Ciudad": ["Santiago", "Santiago"],
        "Guía": ["G001", "G002"],
        "Bultos": [1, 2],
        "Transporte": ["FedEx", "Urbano"]
    })


def test_dry_run():
    print("📦 Iniciando DRY RUN de printer_map...\n")
    errores = 0
    df_ejemplo = generar_df_dummy()

    for modo, funcion in printer_map.items():
        print(f"🔍 Modo: {modo}")
        try:
            funcion(file_path=None, config={}, df=df_ejemplo.copy())
            print(f"✅ {modo}: ejecutado correctamente\n")
        except Exception as e:
            print(f"❌ {modo}: error al ejecutar → {e}\n")
            errores += 1

    if errores == 0:
        print("🎉 Todas las funciones de impresión pasaron el dry run correctamente.")
    else:
        print(f"⚠️ Se detectaron {errores} errores durante la simulación.")

if __name__ == "__main__":
    test_dry_run()
