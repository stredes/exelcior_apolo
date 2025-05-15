import os
import platform
import subprocess
from datetime import datetime
from pathlib import Path
from tkinter import messagebox

from app.utils.logger_setup import log_evento


def print_document(filepath, mode, config_columns, df):
    try:
        if platform.system().lower() != "linux":
            messagebox.showerror("Error", "Este método solo es compatible con Linux.")
            log_evento("Intento de impresión fuera de Linux", "error")
            return

        # Verificar comandos necesarios
        for cmd in ["libreoffice", "lp"]:
            if subprocess.call(["which", cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) != 0:
                raise EnvironmentError(f"El comando '{cmd}' no está disponible en el sistema.")

        # Verificar que la impresora esté definida
        printer_name = os.getenv("PRINTER")
        if not printer_name:
            raise EnvironmentError("La variable de entorno 'PRINTER' no está definida. Usa 'export PRINTER=tu_impresora'.")

        # Directorio para exportar PDF
        output_dir = Path("outputs/pdf").resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_output = output_dir / f"{mode}_impreso_{timestamp}.pdf"

        # Convertir Excel a PDF
        convert_cmd = [
            "libreoffice",
            "--headless",
            "--convert-to", "pdf",
            "--outdir", str(output_dir),
            str(filepath),
        ]
        result = subprocess.run(convert_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        if result.returncode != 0:
            raise RuntimeError(f"Error al convertir a PDF:\n{result.stderr.decode()}")

        generated_pdf = output_dir / Path(filepath).with_suffix(".pdf").name
        if not generated_pdf.exists():
            raise FileNotFoundError("No se encontró el PDF generado.")

        generated_pdf.rename(pdf_output)

        # Enviar a impresora
        print_cmd = ["lp", "-d", printer_name, str(pdf_output)]
        subprocess.run(print_cmd)

        messagebox.showinfo("Impresión", f"📄 Archivo PDF impreso:\n{pdf_output.name}")
        log_evento(f"✅ Documento enviado a impresora: {pdf_output.name}", "info")

        # ✅ OPCIONAL: eliminar archivo PDF después de imprimir
        # os.remove(pdf_output)

    except Exception as e:
        messagebox.showerror("Error", f"❌ Error impresión en Linux:\n{e}")
        log_evento(f"❌ Error al imprimir documento: {e}", "error")
