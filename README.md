# Exelcior Apolo v3.0.0

**Transformador Inteligente de Excel para Operaciones Logísticas**

Una aplicación desktop multiplataforma desarrollada por Gian Lucas San Martín - GCNJ para el procesamiento eficiente de archivos Excel en operaciones logísticas.

## 🚀 Características Principales

### ✨ Funcionalidades Core
- **Procesamiento Inteligente**: Carga y transforma archivos Excel con validación automática
- **Múltiples Modos**: FedEx, Urbano y Listados con configuraciones específicas
- **Auto-detección**: Identifica automáticamente el tipo de archivo y modo apropiado
- **Exportación Flexible**: PDF, impresión directa e impresoras Zebra
- **Base de Datos**: Historial completo de operaciones con SQLite
- **Interfaz Moderna**: GUI intuitiva con diseño responsive

### 🔧 Mejoras Técnicas v2.0
- **Arquitectura Refactorizada**: Código modular con separación clara de responsabilidades
- **Configuración Centralizada**: Sistema unificado de configuración sin duplicación
- **Manejo Robusto de Errores**: Excepciones personalizadas y logging avanzado
- **Validación Completa**: Validadores centralizados para todos los tipos de datos
- **Multiplataforma**: Soporte nativo para Windows y Linux
- **Type Hints**: Tipado completo para mejor mantenibilidad

## 📋 Requisitos del Sistema

### Mínimos
- **Sistema Operativo**: Windows 10+ o Linux (Ubuntu 18.04+)
- **Python**: 3.8 o superior
- **RAM**: 4 GB mínimo, 8 GB recomendado
- **Espacio**: 500 MB libres

### Recomendados
- **Python**: 3.11+
- **RAM**: 16 GB para archivos grandes
- **SSD**: Para mejor rendimiento

## 🛠️ Instalación

### Opción 1: Instalación Rápida (Recomendada)

```bash
# Clonar o extraer el proyecto
cd exelcior_apolo_improved

# Crear entorno virtual
python -m venv venv

# Activar entorno virtual
# Windows:
venv\\Scripts\\activate
# Linux/Mac:
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar aplicación
python src/main.py
```

### Opción 2: Instalación Manual

```bash
# Instalar dependencias individuales
pip install pandas openpyxl xlrd sqlalchemy fpdf2 pillow

# Ejecutar aplicación
python src/main.py
```

## 🎯 Guía de Uso

### Inicio Rápido

1. **Ejecutar la aplicación**
   ```bash
   python src/main.py
   ```

2. **Seleccionar archivo**
   - Usar botón "📁 Seleccionar Archivo" 
   - O usar auto-carga con "🔄 Auto-cargar"

3. **Elegir modo de operación**
   - **FedEx**: Para envíos internacionales
   - **Urbano**: Para entregas locales
   - **Listados**: Para procesamiento general

4. **Procesar datos**
   - Hacer clic en "⚡ Procesar"
   - Revisar datos en la pestaña "📊 Datos"

5. **Exportar o imprimir**
   - "📄 Exportar PDF": Genera archivo PDF
   - "🖨️ Imprimir": Opciones de impresión

### Modos de Operación

#### 🚚 Modo FedEx
- **Propósito**: Procesamiento de envíos FedEx
- **Columnas requeridas**: SHIPDATE, MASTERTRACKINGNUMBER, REFERENCE, RECIPIENTCITY, RECIPIENTCONTACTNAME, PIECETRACKINGNUMBER
- **Funcionalidad**: Agrupa por tracking number y cuenta bultos

#### 🏙️ Modo Urbano
- **Propósito**: Entregas urbanas y locales
- **Columnas requeridas**: FECHA, CLIENTE, CIUDAD, PIEZAS
- **Funcionalidad**: Suma total de piezas por entrega

#### 📋 Modo Listados
- **Propósito**: Procesamiento general flexible
- **Columnas requeridas**: Ninguna (flexible)
- **Funcionalidad**: Procesamiento sin transformaciones específicas

### Configuración Avanzada

#### Rutas Personalizadas
```python
# Configurar directorio personalizado para un modo
from exelcior.core import autoloader
autoloader.set_custom_directory("fedex", "/ruta/personalizada")
```

#### Configuración de Red
```python
# Configurar impresora Zebra
from exelcior.config import config_manager
config_manager.update_network_config(
    zebra_ip="192.168.1.100",
    zebra_port=9100
)
```

## 📁 Estructura del Proyecto

```
exelcior_apolo_improved/
├── src/
│   ├── exelcior/
│   │   ├── __init__.py
│   │   ├── constants.py          # Constantes globales
│   │   ├── config/               # Sistema de configuración
│   │   │   ├── __init__.py
│   │   │   └── manager.py
│   │   ├── core/                 # Lógica de negocio
│   │   │   ├── __init__.py
│   │   │   ├── excel_processor.py
│   │   │   └── autoloader.py
│   │   ├── database/             # Persistencia de datos
│   │   │   ├── __init__.py
│   │   │   └── manager.py
│   │   ├── gui/                  # Interfaz gráfica
│   │   │   ├── __init__.py
│   │   │   └── main_window.py
│   │   ├── printer/              # Sistema de impresión
│   │   │   ├── __init__.py
│   │   │   └── manager.py
│   │   └── utils/                # Utilidades
│   │       ├── __init__.py
│   │       ├── logging.py
│   │       ├── exceptions.py
│   │       └── validators.py
│   └── main.py                   # Punto de entrada
├── tests/                        # Tests unitarios
├── docs/                         # Documentación
├── assets/                       # Recursos
├── config/                       # Archivos de configuración
├── logs/                         # Archivos de log
├── exports/                      # Archivos exportados
├── requirements.txt              # Dependencias
└── README.md                     # Este archivo
```

## 🔧 Configuración

### Archivos de Configuración

La aplicación genera automáticamente archivos de configuración en el directorio `config/`:

- `database.json`: Configuración de base de datos
- `network.json`: Configuración de red e impresoras
- `stock.json`: Configuración de umbrales de stock
- `user.json`: Preferencias del usuario

### Variables de Entorno

```bash
# Opcional: Configurar nivel de logging
export EXELCIOR_LOG_LEVEL=DEBUG

# Opcional: Directorio personalizado de configuración
export EXELCIOR_CONFIG_DIR=/ruta/personalizada
```

## 📊 Logging y Monitoreo

### Archivos de Log

Los logs se almacenan en el directorio `logs/` con rotación automática:

- `exelcior.main.log`: Log principal de la aplicación
- `exelcior.core.log`: Procesamiento de archivos
- `exelcior.database.log`: Operaciones de base de datos
- `exelcior.gui.log`: Eventos de interfaz gráfica
- `exelcior.printer.log`: Operaciones de impresión

### Niveles de Log

- **DEBUG**: Información detallada para desarrollo
- **INFO**: Operaciones normales
- **WARNING**: Situaciones que requieren atención
- **ERROR**: Errores que no detienen la aplicación
- **CRITICAL**: Errores críticos que requieren intervención

## 🧪 Testing

### Ejecutar Tests

```bash
# Todos los tests
python -m pytest tests/

# Tests específicos
python -m pytest tests/unit/
python -m pytest tests/integration/

# Con cobertura
python -m pytest tests/ --cov=src/exelcior
```

### Estructura de Tests

```
tests/
├── unit/                    # Tests unitarios
│   ├── test_excel_processor.py
│   ├── test_config_manager.py
│   └── test_validators.py
└── integration/             # Tests de integración
    ├── test_full_workflow.py
    └── test_database_operations.py
```

## 🚀 Desarrollo

### Configuración del Entorno de Desarrollo

```bash
# Instalar dependencias de desarrollo
pip install -r requirements-dev.txt

# Pre-commit hooks
pre-commit install

# Linting
flake8 src/
black src/
mypy src/
```

### Contribuir

1. Fork el proyecto
2. Crear rama feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit cambios (`git commit -am 'Añadir nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Crear Pull Request

## 📈 Rendimiento

### Optimizaciones Implementadas

- **Carga Lazy**: Los archivos se cargan bajo demanda
- **Procesamiento por Chunks**: Archivos grandes se procesan en fragmentos
- **Cache Inteligente**: Resultados frecuentes se almacenan en cache
- **Threading**: Operaciones pesadas en hilos separados
- **Validación Temprana**: Errores se detectan antes del procesamiento

### Benchmarks

| Operación | Archivo 1K filas | Archivo 10K filas | Archivo 100K filas |
|-----------|------------------|-------------------|---------------------|
| Carga     | < 1s            | < 3s              | < 15s               |
| Procesamiento | < 0.5s      | < 2s              | < 10s               |
| Exportación PDF | < 2s       | < 5s              | < 30s               |

## 🔒 Seguridad

### Medidas Implementadas

- **Validación de Entrada**: Todos los inputs son validados
- **Sanitización**: Datos se limpian antes del procesamiento
- **Manejo Seguro de Archivos**: Validación de tipos y tamaños
- **Logging Seguro**: No se registran datos sensibles
- **Configuración Segura**: Archivos de configuración con permisos restringidos

## 🐛 Solución de Problemas

### Problemas Comunes

#### Error: "Módulo no encontrado"
```bash
# Verificar que está en el directorio correcto
cd exelcior_apolo_improved

# Verificar entorno virtual
python -c "import sys; print(sys.path)"

# Reinstalar dependencias
pip install -r requirements.txt
```

#### Error: "Archivo no se puede abrir"
- Verificar que el archivo no esté abierto en Excel
- Comprobar permisos de lectura
- Verificar formato de archivo soportado

#### Error: "Impresora no disponible"
- Verificar conexión de red para impresoras Zebra
- Comprobar drivers de impresora del sistema
- Revisar configuración de IP y puerto

#### Rendimiento lento
- Cerrar otras aplicaciones que consuman memoria
- Usar archivos más pequeños para pruebas
- Verificar espacio disponible en disco

### Logs de Diagnóstico

```bash
# Habilitar logging detallado
export EXELCIOR_LOG_LEVEL=DEBUG
python src/main.py

# Revisar logs
tail -f logs/exelcior.main.log
```

## 📞 Soporte

### Información de Contacto

- **Desarrollador**: Gian Lucas San Martín - GCNJ
- **Email**: [contacto disponible en el código fuente]
- **Versión**: 2.0.0
- **Fecha**: 2025

### Reportar Problemas

1. Revisar la sección de solución de problemas
2. Verificar logs en el directorio `logs/`
3. Incluir información del sistema y pasos para reproducir
4. Adjuntar archivos de log relevantes

## 📄 Licencia

Este proyecto es software propietario desarrollado por Gian Lucas San Martín - GCNJ.
Todos los derechos reservados.

## 🎉 Agradecimientos

- **Pandas**: Por el excelente manejo de datos
- **SQLAlchemy**: Por el ORM robusto
- **Tkinter**: Por la interfaz gráfica multiplataforma
- **FPDF**: Por la generación de PDFs
- **Comunidad Python**: Por las herramientas y librerías

---

**Exelcior Apolo v2.0.0** - Transformando la gestión logística con tecnología moderna.

*Desarrollado con ❤️ por Gian Lucas San Martín - GCNJ*

