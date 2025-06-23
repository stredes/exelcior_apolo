#!/usr/bin/env python3
"""
Script de pruebas completo para Exelcior Apolo
Valida todas las funcionalidades implementadas
"""

import sys
import os
import tempfile
import pandas as pd
from pathlib import Path

# Agregar directorio src al path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Probar todas las importaciones"""
    print("🧪 PRUEBA 1: Importaciones")
    print("=" * 50)
    
    try:
        from exelcior.core.integrated_processor import IntegratedExcelProcessor
        print("✅ IntegratedExcelProcessor")
    except Exception as e:
        print(f"❌ IntegratedExcelProcessor: {e}")
        return False
    
    try:
        from exelcior.core.urbano_system import UrbanoDetectionSystem, UrbanoProcessor
        print("✅ Sistema urbano")
    except Exception as e:
        print(f"❌ Sistema urbano: {e}")
        return False
    
    try:
        from exelcior.gui.config_window import ConfigurationWindow
        print("✅ ConfigurationWindow")
    except Exception as e:
        print(f"❌ ConfigurationWindow: {e}")
        return False
    
    try:
        from exelcior.modules.additional_tools import ToolsModule, LabelEditor, SearchModule
        print("✅ Módulos adicionales")
    except Exception as e:
        print(f"❌ Módulos adicionales: {e}")
        return False
    
    print("✅ Todas las importaciones exitosas\n")
    return True

def test_urbano_detection():
    """Probar sistema de detección urbana"""
    print("🧪 PRUEBA 2: Detección Urbana")
    print("=" * 50)
    
    from exelcior.core.urbano_system import UrbanoDetectionSystem
    
    detector = UrbanoDetectionSystem()
    
    # Pruebas de nombres de archivo
    test_cases = [
        ("192403809.xlsx", True),
        ("1924038091.xlsx", True),
        ("fedex_report.xlsx", False),
        ("lista_venta.xlsx", False),
        ("123456789.xls", True),
        ("12345678.xlsx", False),  # 8 dígitos
        ("12345678901.xlsx", False)  # 11 dígitos
    ]
    
    print("📁 Detección por nombre de archivo:")
    all_passed = True
    for filename, expected in test_cases:
        result = detector.is_urbano_filename(filename)
        status = "✅" if result == expected else "❌"
        print(f"  {status} {filename}: {result} (esperado: {expected})")
        if result != expected:
            all_passed = False
    
    # Pruebas de estructura
    print("\n📊 Validación de estructura:")
    
    # DataFrame válido
    df_valid = pd.DataFrame({
        'FECHA': ['2025-06-23'],
        'CLIENTE': ['CLIENTE_A'],
        'CIUDAD': ['CHILLAN'],
        'PIEZAS': [5]
    })
    
    is_valid, missing = detector.validate_urbano_structure(df_valid)
    status = "✅" if is_valid else "❌"
    print(f"  {status} Estructura válida: {is_valid}")
    
    # DataFrame inválido
    df_invalid = pd.DataFrame({
        'FECHA': ['2025-06-23'],
        'NOMBRE': ['CLIENTE_A']  # Falta CLIENTE, CIUDAD, PIEZAS
    })
    
    is_valid, missing = detector.validate_urbano_structure(df_invalid)
    status = "✅" if not is_valid else "❌"
    print(f"  {status} Estructura inválida: {not is_valid} (columnas faltantes: {len(missing)})")
    
    print(f"{'✅' if all_passed else '❌'} Pruebas de detección urbana {'exitosas' if all_passed else 'fallidas'}\n")
    return all_passed

def test_mode_detection():
    """Probar detección automática de modos"""
    print("🧪 PRUEBA 3: Detección de Modos")
    print("=" * 50)
    
    from exelcior.core.integrated_processor import IntegratedExcelProcessor
    
    processor = IntegratedExcelProcessor()
    
    test_cases = [
        ("192403809.xlsx", "urbano"),
        ("1924038091.xlsx", "urbano"),
        ("fedex_report.xlsx", "fedex"),
        ("shipment_data.xlsx", "fedex"),
        ("lista_venta_20250623.xlsx", "listados"),
        ("listado_productos.xlsx", "listados"),
        ("archivo_generico.xlsx", "listados")  # Por defecto
    ]
    
    all_passed = True
    for filename, expected_mode in test_cases:
        detected_mode = processor.detect_file_mode(filename)
        status = "✅" if detected_mode == expected_mode else "❌"
        print(f"  {status} {filename}: {detected_mode} (esperado: {expected_mode})")
        if detected_mode != expected_mode:
            all_passed = False
    
    print(f"{'✅' if all_passed else '❌'} Pruebas de detección de modos {'exitosas' if all_passed else 'fallidas'}\n")
    return all_passed

def test_data_processing():
    """Probar procesamiento de datos"""
    print("🧪 PRUEBA 4: Procesamiento de Datos")
    print("=" * 50)
    
    from exelcior.core.integrated_processor import IntegratedExcelProcessor
    
    processor = IntegratedExcelProcessor()
    
    # Crear datos de prueba para cada modo
    test_data = {
        "urbano": pd.DataFrame({
            'FECHA': ['2025-06-23', '2025-06-23', '2025-06-23'],
            'CLIENTE': ['CLIENTE_A', 'CLIENTE_B', 'CLIENTE_C'],
            'CIUDAD': ['CHILLAN', 'SANTIAGO', 'CONCEPCION'],
            'PIEZAS': [5, 3, 7],
            'AGENCIA': ['AG001', 'AG002', 'AG003'],
            'PESO': [10.5, 8.2, 15.3]
        }),
        "fedex": pd.DataFrame({
            'SHIPDATE': ['2025-06-23', '2025-06-23', '2025-06-23'],
            'MASTERTRACKINGNUMBER': ['TRK001', 'TRK001', 'TRK002'],
            'REFERENCE': ['REF001', 'REF001', 'REF002'],
            'RECIPIENTCITY': ['CHILLAN', 'CHILLAN', 'SANTIAGO'],
            'RECIPIENTCONTACTNAME': ['CLIENTE_A', 'CLIENTE_A', 'CLIENTE_B'],
            'PIECETRACKINGNUMBER': ['PCE001', 'PCE002', 'PCE003']
        }),
        "listados": pd.DataFrame({
            'FECHA': ['2025-06-23', '2025-06-23'],
            'CLIENTE': ['CLIENTE_A', 'CLIENTE_B'],
            'PRODUCTO': ['PROD_X', 'PROD_Y'],
            'TOTAL': [1500, 2300],
            'MONEDA': ['CLP', 'CLP']  # Se eliminará
        })
    }
    
    all_passed = True
    
    for mode, df in test_data.items():
        print(f"📊 Probando modo {mode.upper()}:")
        
        try:
            # Crear archivo temporal
            with tempfile.NamedTemporaryFile(suffix=f'_{mode}_test.xlsx', delete=False) as tmp:
                df.to_excel(tmp.name, index=False)
                temp_file = tmp.name
            
            # Procesar archivo
            result = processor.process_file_complete(temp_file, mode)
            
            if result['success']:
                print(f"  ✅ Procesamiento exitoso")
                print(f"    - Registros: {result['summary']['total_records']}")
                
                if mode == "urbano" and 'total_piezas' in result['summary']:
                    print(f"    - Total piezas: {result['summary']['total_piezas']}")
                elif mode == "fedex" and 'total_bultos' in result['summary']:
                    print(f"    - Total bultos: {result['summary']['total_bultos']}")
                
            else:
                print(f"  ❌ Error: {result['error']}")
                all_passed = False
            
            # Limpiar archivo temporal
            os.unlink(temp_file)
            
        except Exception as e:
            print(f"  ❌ Excepción: {e}")
            all_passed = False
    
    print(f"{'✅' if all_passed else '❌'} Pruebas de procesamiento {'exitosas' if all_passed else 'fallidas'}\n")
    return all_passed

def test_configuration():
    """Probar sistema de configuración"""
    print("🧪 PRUEBA 5: Sistema de Configuración")
    print("=" * 50)
    
    from exelcior.core.integrated_processor import IntegratedExcelProcessor
    
    processor = IntegratedExcelProcessor()
    
    # Verificar configuración por defecto
    config = processor.config
    
    required_modes = ["urbano", "fedex", "listados"]
    all_passed = True
    
    for mode in required_modes:
        if mode in config:
            print(f"✅ Configuración {mode}: presente")
            
            # Verificar claves requeridas
            required_keys = ["eliminar", "sumar", "mantener_formato", "start_row"]
            for key in required_keys:
                if key in config[mode]:
                    print(f"  ✅ {key}: {type(config[mode][key]).__name__}")
                else:
                    print(f"  ❌ {key}: faltante")
                    all_passed = False
        else:
            print(f"❌ Configuración {mode}: faltante")
            all_passed = False
    
    print(f"{'✅' if all_passed else '❌'} Pruebas de configuración {'exitosas' if all_passed else 'fallidas'}\n")
    return all_passed

def run_all_tests():
    """Ejecutar todas las pruebas"""
    print("🚀 INICIANDO PRUEBAS COMPLETAS DE EXELCIOR APOLO")
    print("=" * 60)
    print()
    
    tests = [
        test_imports,
        test_urbano_detection,
        test_mode_detection,
        test_data_processing,
        test_configuration
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Error en prueba: {e}")
            results.append(False)
    
    # Resumen final
    print("📊 RESUMEN DE PRUEBAS")
    print("=" * 60)
    
    test_names = [
        "Importaciones",
        "Detección Urbana",
        "Detección de Modos",
        "Procesamiento de Datos",
        "Sistema de Configuración"
    ]
    
    passed = sum(results)
    total = len(results)
    
    for i, (name, result) in enumerate(zip(test_names, results)):
        status = "✅ PASÓ" if result else "❌ FALLÓ"
        print(f"{i+1}. {name}: {status}")
    
    print()
    print(f"📈 RESULTADO FINAL: {passed}/{total} pruebas exitosas")
    
    if passed == total:
        print("🎉 ¡TODAS LAS PRUEBAS PASARON! El sistema está funcionando correctamente.")
        return True
    else:
        print("⚠️  Algunas pruebas fallaron. Revisar los errores anteriores.")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

