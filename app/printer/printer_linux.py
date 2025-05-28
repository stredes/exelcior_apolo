import os
import platform
import subprocess
from pathlib import Path
from datetime import datetime
from tkinter import messagebox

from app.core.logger_eventos import log_evento  # ✅ logging unificado


def print_document(filepath, mode, config_columns, df):
    try:
        if platform.system().lower() != "linux":
            log_evento("Intento de impresión en SO no compatible (no Linux)", "warning")
            messagebox.showerror("Error", "Este método solo es compatible con Linux.")
            return

        # Verificar comandos necesarios
        for cmd in ["libreoffice", "lp"]:
            if subprocess.call(["which", cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) != 0:
                raise EnvironmentError(f"{cmd} no está disponible en el sistema.")

        output_dir = Path("outputs/pdf").resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_output = output_dir / f"{mode}_impreso_{timestamp}.pdf"

        # Convertir Excel a PDF
        convert_cmd = [
            "libreoffice", "--headless",
            "--convert-to", "pdf",
            "--outdir", str(output_dir),
            str(filepath)
        ]
        result = subprocess.run(convert_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        if result.returncode != 0:
            raise RuntimeError(f"Error al convertir a PDF:\n{result.stderr.decode()}")

        generated_pdf = output_dir / Path(filepath).with_suffix('.pdf').name
        if not generated_pdf.exists():
            raise FileNotFoundError("No se encontró el PDF generado.")

        generated_pdf.rename(pdf_output)

        # Imprimir PDF
        print_cmd = ["lp", "-d", os.getenv("PRINTER", ""), str(pdf_output)]
        subprocess.run(print_cmd)

        log_evento(f"PDF generado e impreso correctamente: {pdf_output}", "info")
        messagebox.showinfo("Impresión", f"Archivo PDF impreso:\n{pdf_output.name}")

    except Exception as e:
        log_evento(f"Error impresión en Linux: {e}", "error")
        messagebox.showerror("Error", f"Error impresión en Linux:\n{e}")
