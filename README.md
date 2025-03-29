""# 📊 Exelcior Apolo – Transformador Inteligente de Excel

[![Python](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/github/license/stredes/exelcior_apolo)](LICENSE)
[![Estado](https://img.shields.io/badge/estado-en%20desarrollo-yellow.svg)]()
[![Repo](https://img.shields.io/badge/github-exelcior--apolo-000?logo=github)](https://github.com/stredes/exelcior_apolo)

Transformador de archivos Excel para operaciones logísticas, generación de reportes, filtrado automatizado y emisión directa en PDF o impresión. Optimizado para flujos de trabajo con FedEx, Urbano y Listados comerciales.

> Aplicación de escritorio multiplataforma con GUI desarrollada en Python, usando Tkinter y funciones avanzadas de análisis de datos con pandas.

---

## 🚀 Características

- 🔍 **Autodetección automática de archivos Excel** desde la carpeta `Descargas/` por tipo de operación
- 📤 **Exportación instantánea a PDF** o impresión directa
- 📁 **Historial persistente** de archivos procesados en base SQLite
- ⚙️ **Configuración personalizada** de columnas a eliminar, sumar o mantener
- 📄 **Vista previa interactiva** y validación de datos
- 🧠 **Modos de operación inteligentes**: `FedEx`, `Urbano`, `Listados`
- 🌗 Interfaz clara, ligera y moderna, con tema oscuro
- 💻 Compatible con Linux y Windows

---

## 🛠️ Tecnologías

- Python 3.12
- Tkinter (GUI)
- pandas / openpyxl
- SQLite3
- ReportLab y LibreOffice (para impresión PDF)
- Git / GitHub

---

## 📦 Instalación

### Clona el proyecto

```bash
git clone https://github.com/stredes/exelcior_apolo.git
cd exelcior_apolo
Activa entorno virtual
bash
Mostrar siempre los detalles

Copiar
python3 -m venv .venv
source .venv/bin/activate   # En Windows: .venv\\Scripts\\activate
Instala dependencias
bash
Mostrar siempre los detalles

Copiar
pip install -r requirements.txt
Ejecuta la app
bash
Mostrar siempre los detalles

Copiar
python main_app.py
📂 Modos y estructura esperada
FedEx
Archivos tipo Shipment_Report_YYYY-MM-DD.xlsx

Aplica reglas de eliminación y suma por numberOfPackages

Urbano
Archivos con exactamente 9 dígitos numéricos en su nombre (211823030.xlsx)

Usa start_row: 2 y suma la columna PIEZAS

Listados
Archivos lista_doc_venta_YYYYMMDD_HHMMSS.xlsx

Elimina campos contables como Glosa, Vendedor, RUT, etc.

🧠 Uso de la App
🖱️ Selecciona un modo (urbano, fedex, listados)

📂 Carga manualmente un Excel o usa el botón Carga Automática 🚀

👁️ Visualiza la transformación

📄 Exporta o 🖨️ Imprime directamente

🔧 Configuración por modo
Editable desde GUI (⚙️ Configuración):

json
Mostrar siempre los detalles

Copiar
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
📁 Estructura del Proyecto
bash
Mostrar siempre los detalles

Copiar
app_excel/
│
├── printer/                 # Exportación e impresión
├── db/                      # Base de datos y modelos
├── utils/                   # Carga, logs y herramientas
├── data/                    # BD local
├── autoloader.py            # Autocarga de archivos recientes
├── excel_processor.py       # Transformaciones de datos
├── main_app.py              # App principal con GUI
├── config_dialog.py         # Configurador visual de columnas
├── requirements.txt
└── README.md
🧪 Debug y Logs
Los errores y operaciones se registran en logs/logs_app.log

Accesibles desde GUI (📋 Ver Logs)

🤝 Contribuciones
¿Quieres colaborar? ¡Sigue estos pasos!

bash
Mostrar siempre los detalles

Copiar
# Crea una rama nueva
git checkout -b feature/nueva-funcionalidad

# Haz tus cambios
git add .
git commit -m "feat: nueva funcionalidad"
git push origin feature/nueva-funcionalidad
Y abre un Pull Request desde GitHub.

👤 Autor
Gian Lucas
Técnico de laboratorio clínico – Desarrollador Python
GitHub: @stredes

📄 Licencia
Distribuido bajo la licencia Apache 2.0.
Consulta el archivo LICENSE para más detalles.

📬 Contacto
¿Tienes preguntas o sugerencias?
Abre un Issue """

Guardar en README.md
readme_path = Path("README.md") readme_path.write_text(readme_content, encoding="utf-8")

readme_path.absolute()

Mostrar siempre los detalles

Copiar
Resultado
PosixPath('/home/sandbox/README.md')
✅ El README.md fue generado exitosamente y guardado en el proyecto.

Ahora puedes hacer:

bash
Copiar
Editar
git add README.md
git commit -m "docs: actualizar README con autoloader, estructura y badges"
git push origin main