from pathlib import Path
from datetime import datetime
import pandas as pd
import tempfile
import smtplib
from email.message import EmailMessage
from typing import Optional, Dict, List, Any
import json
import logging

USER_CONFIG_FILE = Path("config/user_config.json")

# ------------------- CONFIGURACIÓN -------------------

def cargar_config_usuario() -> Dict[str, Any]:
    """
    Carga la configuración del usuario desde archivo JSON.
    """
    if USER_CONFIG_FILE.exists():
        with USER_CONFIG_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def guardar_config_usuario(config: Dict[str, Any]) -> None:
    """
    Guarda la configuración del usuario en archivo JSON.
    """
    with USER_CONFIG_FILE.open("w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)

# ------------------- EXPORTACIÓN -------------------

def exportar_csv_a_path(df: pd.DataFrame, path: Path) -> None:
    """
    Exporta un DataFrame a un archivo CSV.
    """
    df.to_csv(path, index=False)

def exportar_xlsx_a_path(df: pd.DataFrame, path: Path) -> None:
    """
    Exporta un DataFrame a un archivo Excel.
    """
    df.to_excel(path, index=False)

def exportar_pdf_a_path(df: pd.DataFrame, path: Path) -> None:
    """
    Exporta un DataFrame a PDF con formato simple usando ReportLab.
    """
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    c = canvas.Canvas(str(path), pagesize=letter)
    width, height = letter
    y = height - 40
    c.setFont("Helvetica", 10)

    # Encabezados
    for col in df.columns:
        c.drawString(30, y, str(col))
        y -= 15

    y -= 10

    # Datos
    for _, row in df.head(50).iterrows():
        line = ", ".join(str(val) for val in row)
        c.drawString(30, y, line)
        y -= 15
        if y < 40:
            c.showPage()
            y = height - 40

    c.save()

# ------------------- ESTADÍSTICAS -------------------

def obtener_estadisticas(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Obtiene estadísticas básicas del DataFrame.
    """
    return {
        "filas": len(df),
        "columnas": len(df.columns),
        "bultos": df['BULTOS'].sum() if 'BULTOS' in df.columns else None,
        "clientes_unicos": df['Cliente'].nunique() if 'Cliente' in df.columns else None,
        "fechas_envio": df['Fecha'].dropna().unique().tolist() if 'Fecha' in df.columns else None
    }

# ------------------- EDICIÓN DE COLUMNAS -------------------

def aplicar_edicion_columnas(
    df: pd.DataFrame,
    columnas_a_mantener: List[str],
    nuevos_nombres: Dict[str, str]
) -> pd.DataFrame:
    """
    Aplica edición a columnas: filtrado y renombrado.
    """
    df = df[columnas_a_mantener]
    return df.rename(columns=nuevos_nombres)

# ------------------- BÚSQUEDA -------------------

def buscar_por_columna(df: pd.DataFrame, columna: str, valor: str) -> pd.DataFrame:
    """
    Filtra filas cuyo valor en la columna contenga el valor indicado.
    """
    if columna not in df.columns:
        raise ValueError(f"Columna '{columna}' no encontrada.")
    return df[df[columna].astype(str).str.contains(valor, case=False, na=False)]

# ------------------- EMAIL -------------------

def enviar_dataframe_por_email(
    df: pd.DataFrame,
    remitente: str,
    password: str,
    destinatario: str,
    smtp_server: str = 'smtp.tudominio.com',
    smtp_port: int = 587,
    asunto: str = 'Datos Exportados',
    cuerpo: str = 'Adjunto los datos solicitados.'
) -> None:
    """
    Envía un DataFrame como archivo Excel adjunto por correo.
    """
    try:
        # Crear archivo temporal
        temp_path = Path(tempfile.gettempdir()) / f"datos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        df.to_excel(temp_path, index=False)

        # Componer mensaje
        msg = EmailMessage()
        msg['Subject'] = asunto
        msg['From'] = remitente
        msg['To'] = destinatario
        msg.set_content(cuerpo)

        with open(temp_path, "rb") as f:
            msg.add_attachment(
                f.read(),
                maintype="application",
                subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                filename=temp_path.name
            )

        # Enviar
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(remitente, password)
            server.send_message(msg)

        logging.info(f"Correo enviado a {destinatario}")
    except Exception as e:
        logging.error(f"Error al enviar correo: {e}")
        raise
    finally:
        temp_path.unlink(missing_ok=True)
