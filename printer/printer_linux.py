import os
import platform
import subprocess
from pathlib import Path
from datetime import datetime
from tkinter import messagebox

def print_document_linux(temp_excel_path):
    try:
        if platform.system().lower() != "linux":
            messagebox.showerror("Error", "Este método solo es compatible con Linux.")
            return

        # Verificar si libreoffice está instalado
        if subprocess.call(["which", "libreoffice"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) != 0:
            raise EnvironmentError("LibreOffice no está instalado en el sistema.")

        # Verificar si lp está disponible
        if subprocess.call(["which", "lp"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) != 0:
            raise EnvironmentError("El comando 'lp' no está disponible en el sistema.")

        # Crear directorio de salida si no existe
        output_dir = Path("outputs/pdf")
        output_dir.mkdir(parents=True, exist_ok=True)

        # Ruta destino del PDF
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_output = output_dir / f"converted_{timestamp}.pdf"

        # Convertir Excel a PDF usando LibreOffice
        convert_cmd = [
            "libreoffice",
            "--headless",
            "--convert-to", "pdf",
            "--outdir", str(output_dir),
            str(temp_excel_path)
        ]
        result = subprocess.run(convert_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        if result.returncode != 0:
            raise RuntimeError(f"Error al convertir a PDF:\n{result.stderr.decode()}")

        # LibreOffice puede cambiar el nombre del archivo generado
        generated_pdf = output_dir / Path(temp_excel_path).with_suffix('.pdf').name
        if not generated_pdf.exists():
            raise FileNotFoundError("No se encontró el PDF convertido.")

        # Renombrar al formato deseado
        generated_pdf.rename(pdf_output)

        # Enviar a imprimir
        print_cmd = ["lp", str(pdf_output)]
        subprocess.run(print_cmd)

        messagebox.showinfo("Impresión", f"PDF generado y enviado a imprimir:\n{pdf_output.name}")
        return pdf_output

    except Exception as e:
        messagebox.showerror("Error", f"Error impresión en Linux:\n{e}")
