# 📊 Exelcior Apolo – Transformador Inteligente de Excel

[![Python](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/github/license/stredes/exelcior_apolo)](LICENSE)
[![Estado](https://img.shields.io/badge/estado-en%20desarrollo-yellow.svg)]()
[![Repo](https://img.shields.io/badge/github-exelcior--apolo-000?logo=github)](https://github.com/stredes/exelcior_apolo)

Aplicación de escritorio **multiplataforma** para transformar, validar e imprimir archivos Excel de forma automatizada.  
Optimizada para flujos logísticos y clínicos con soporte para **FedEx**, **Urbano**, **Listados comerciales** y **herramientas de inventario y etiquetas**.

---

## 🚀 Características principales

- 🔍 **Autodetección** de archivos Excel en la carpeta de descargas por *modo de operación*
- 🖨️ **Impresión directa** vía Excel COM (Windows) o LibreOffice (Linux/macOS)
- 📤 **Exportación a PDF** de los reportes generados
- ⚙️ **Reglas de transformación configurables** (eliminar, sumar, mantener formato, conservar)
- 👁️ **Vista previa interactiva** con ajuste automático de columnas
- 💾 **Historial persistente** de archivos e impresiones en SQLite
- 🧩 **Modularidad**: cada modo de impresión (FedEx, Urbano, Listados, Inventario, Etiquetas) es independiente
- 🌗 **Interfaz moderna** con Tkinter y soporte de logs integrados
- 💻 Compatible con **Windows** y **Linux**

---

## 🛠️ Tecnologías

- **Python 3.12**
- **Tkinter** (interfaz gráfica)
- **pandas + openpyxl** (procesamiento de Excel)
- **SQLAlchemy + SQLite** (persistencia de historial)
- **ReportLab** (PDF de etiquetas)
- **LibreOffice / Excel COM** (impresión multiplataforma)

---

## 📦 Instalación

### 1. Clonar el repositorio
```bash
git clone https://github.com/stredes/exelcior_apolo.git
cd exelcior_apolo
2. Crear entorno virtual
bash
Copiar
Editar
python3 -m venv .venv
source .venv/bin/activate      # Linux/macOS
.venv\Scripts\activate         # Windows
3. Instalar dependencias
bash
Copiar
Editar
pip install -r requirements.txt
4. Ejecutar la aplicación
bash
Copiar
Editar
python run_app.py

## Actualizaciones automáticas

- Las versiones instaladas consultan `GitHub Releases` al iniciar.
- Si existe una release más nueva con un asset `ExelciorApolo_*_Setup.exe`, la app avisa y descarga el instalador oficial.
- El instalador cierra la app actual y reemplaza la instalación existente.

### Publicar una nueva versión

1. Actualiza la versión objetivo.
2. Crea un tag semántico, por ejemplo `v1.4.2`.
3. Haz `git push origin v1.4.2`.
4. GitHub Actions compilará `PyInstaller`, generará el instalador Inno Setup y publicará los assets en Releases.
📂 Modos de operación
🟣 FedEx
Archivos: Shipment_Report_YYYY-MM-DD.xlsx

Reglas:

sumar: numberOfPackages

mantener_formato: tracking numbers

🔵 Urbano
Archivos: 9 dígitos exactos (211823030.xlsx)

Reglas:

sumar: PIEZAS

start_row: 2 (salta cabecera inicial)

🟢 Listados
Archivos: lista_doc_venta_YYYYMMDD_HHMMSS.xlsx

Reglas:

eliminar: columnas contables (Glosa, Vendedor, RUT, …)

🟠 Inventario
Búsqueda de productos por Código o Ubicación

Impresión de resultados filtrados

🏷️ Etiquetas
Editor de etiquetas 10×10 cm

Exporta PDF temporal y lo envía a la impresora seleccionada

🧠 Uso básico
Selecciona un modo de operación

Carga un Excel manualmente o usa Carga Automática

Visualiza la transformación previa

Exporta a PDF o envía a la impresora

⚙️ Configuración
Editable desde la GUI (Config. Modo ⚙️) o manualmente en:

Linux/macOS: ~/.exelcior_apolo/excel_print_config.json

Windows: %USERPROFILE%\.exelcior_apolo\excel_print_config.json

Ejemplo de reglas por modo:

json
Copiar
Editar
{
  "modes": {
    "fedex": {
      "eliminar": ["senderEmail", "senderCity", "..."],
      "sumar": ["numberOfPackages"],
      "mantener_formato": ["masterTrackingNumber"]
    },
    "urbano": {
      "eliminar": ["SERVICIO", "AGENCIA", "..."],
      "sumar": ["PIEZAS"],
      "start_row": 2
    }
  }
}
🧪 Logs y Debug
logs/app.log → registros técnicos (errores, stacktrace)

logs/eventos.log → trazabilidad funcional (archivos cargados, sumatorias, impresiones)

Acceso directo desde la app vía menú 📋 Ver Logs.

🤝 Contribución
Haz un fork del repositorio

Crea una rama:

bash
Copiar
Editar
git checkout -b feature/nueva-funcionalidad
Haz tus cambios y commits descriptivos

Sube tu rama y abre un Pull Request 🚀

👤 Autor
Gian Lucas San Martín
Técnico de Laboratorio Clínico – Analista Programador Python
GitHub: @stredes

📄 Licencia
Distribuido bajo Apache 2.0.
Consulta el archivo LICENSE para más detalles.
