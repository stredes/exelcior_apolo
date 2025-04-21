import re
from pathlib import Path
from collections import defaultdict

def analizar_logs():
    log_dir = Path("logs")
    if not log_dir.exists():
        print("❌ Carpeta 'logs/' no encontrada.")
        return

    logs = sorted(log_dir.glob("*.log"))
    if not logs:
        print("⚠️  No hay archivos de log disponibles.")
        return

    errores_encontrados = defaultdict(list)

    patrones = {
        "Carga automática fallida": re.compile(r"Error en carga automática", re.IGNORECASE),
        "Fallo de impresión": re.compile(r"Error en impresión", re.IGNORECASE),
        "Error de lectura": re.compile(r"Error al leer el archivo", re.IGNORECASE),
        "Error en transformación": re.compile(r"Error en transformación", re.IGNORECASE),
        "Permiso denegado": re.compile(r"Permission denied", re.IGNORECASE),
        "Objeto sin atributo": re.compile(r"object has no attribute", re.IGNORECASE),
        "Otros errores": re.compile(r"- ERROR - (.+)")
    }

    for log_file in logs:
        with log_file.open("r", encoding="utf-8", errors="ignore") as f:
            for linea in f:
                for categoria, patron in patrones.items():
                    if patron.search(linea):
                        errores_encontrados[categoria].append((log_file.name, linea.strip()))
                        break

    print("\n📊 RESUMEN DE ERRORES EN LOGS:")
    print("──────────────────────────────")
    if not errores_encontrados:
        print("✅ No se detectaron errores relevantes.")
        return

    for categoria, eventos in errores_encontrados.items():
        print(f"\n🔹 {categoria} ({len(eventos)} encontrados)")
        for archivo, mensaje in eventos[-3:]:  # muestra los últimos 3
            print(f"  • {archivo} → {mensaje}")

if __name__ == "__main__":
    analizar_logs()