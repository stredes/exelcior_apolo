# 📊 Exelcior Apolo – Transformador Inteligente de Excel

[![Python](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/github/license/stredes/exelcior_apolo)](LICENSE)
[![Estado](https://img.shields.io/badge/estado-en%20desarrollo-yellow.svg)]()
[![Repo](https://img.shields.io/badge/github-exelcior--apolo-000?logo=github)](https://github.com/stredes/exelcior_apolo)

Transformador de archivos Excel para operaciones logísticas, generación de reportes, filtrado automatizado y emisión directa en PDF o impresión. Optimizado para flujos de trabajo con **FedEx**, **Urbano** y **Listados comerciales**.

> Aplicación de escritorio multiplataforma con GUI desarrollada en Python, usando Tkinter y funciones avanzadas de análisis de datos con Pandas.

---

## 🚀 Características

- 🔍 Autodetección de archivos Excel desde la carpeta `Descargas/` según el tipo de operación
- 📤 Exportación instantánea a PDF o impresión directa por impresora predeterminada
- 💾 Historial persistente de archivos procesados usando SQLite
- ⚙️ Configuración flexible de columnas a eliminar, mantener o sumar
- 👁️ Vista previa interactiva con filtros y validación visual
- 🧠 Modos inteligentes de operación: `FedEx`, `Urbano`, `Listados`
- 🌗 Interfaz moderna, clara y ligera con soporte para modo oscuro
- 💻 Compatible con Linux y Windows

---

## 🛠️ Tecnologías

- Python 3.12
- Tkinter (GUI)
- pandas / openpyxl
- SQLite3
- ReportLab / LibreOffice (PDF e impresión)
- Git / GitHub

---

## 📦 Instalación

### 1. Clonar el proyecto

```bash
git clone https://github.com/stredes/exelcior_apolo.git
cd exelcior_apolo
```

### 2. Crear entorno virtual

```bash
python3 -m venv .venv
source .venv/bin/activate  # En Windows: .venv\Scripts\activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Ejecutar la aplicación

```bash
python main_app.py
```

---

## 📂 Modos de operación y estructura de archivos esperada

### 🟣 FedEx

- Archivos: `Shipment_Report_YYYY-MM-DD.xlsx`
- Suma: `numberOfPackages`
- Elimina columnas irrelevantes por configuración

### 🔵 Urbano

- Archivos: 9 dígitos exactos, e.g. `211823030.xlsx`
- Suma: `PIEZAS`
- Empieza a leer desde la fila 3 (`start_row: 2`)

### 🟢 Listados

- Archivos: `lista_doc_venta_YYYYMMDD_HHMMSS.xlsx`
- Elimina columnas contables como `Glosa`, `Vendedor`, `RUT`, etc.

---

## 🧠 Uso de la App

🖱️ Selecciona un modo (Urbano, FedEx, Listados)  
📂 Carga un Excel manualmente o usa Carga Automática  
👁️ Visualiza la transformación previa  
📄 Exporta o 🖨️ Imprime directamente

---

## ⚙️ Configuración por modo

Editable desde la interfaz de configuración (⚙️).  
También puedes modificar manualmente el archivo `excel_printer_config.json`.

```json
{
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
```

---

## 🧪 Debug y Logs

Los errores y operaciones se registran automáticamente en `logs/logs_app.log`.  
Puedes acceder a ellos desde la GUI (📋 Ver Logs).

---

## 🤝 Contribuciones

¿Quieres colaborar? ¡Sigue estos pasos!

```bash
# Crea una rama nueva
git checkout -b feature/nueva-funcionalidad

# Haz tus cambios
git add .
git commit -m "feat: nueva funcionalidad"
git push origin feature/nueva-funcionalidad
```

Luego abre un Pull Request desde GitHub.

---

## 👤 Autor

**Gian Lucas San Martín**  
Técnico de laboratorio clínico – Desarrollador Python  
GitHub: [@stredes](https://github.com/stredes)

---

## 📄 Licencia

Distribuido bajo la licencia Apache 2.0.  
Consulta el archivo LICENSE para más detalles.