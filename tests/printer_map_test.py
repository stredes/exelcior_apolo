# Módulo: printer_map_test.py
# Descripción: Verifica que todas las funciones registradas en printer_map existan y sean llamables

from app.services.file_service import printer_map

def test_printer_map():
    print("📋 Verificando printer_map...\n")
    errores = 0
    for modo, funcion in printer_map.items():
        if callable(funcion):
            print(f"✅ '{modo}' => función registrada correctamente: {funcion.__name__}")
        else:
            print(f"❌ '{modo}' => NO es una función válida.")
            errores += 1

    if errores == 0:
        print("\n🎉 Todos los modos tienen funciones válidas registradas.")
    else:
        print(f"\n⚠️ Se encontraron {errores} errores en el registro de printer_map.")

if __name__ == "__main__":
    test_printer_map()
