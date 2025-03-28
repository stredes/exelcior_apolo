import os
import platform
import subprocess
from pathlib import Path
from datetime import datetime
from tkinter import messagebox

def print_document_linux(temp_excel_path, printer_name=None, copies=1, options=None):
    try:
        if platform.system().lower() != "linux":
            messagebox.showerror("Error", "Este método solo es compatible con Linux.")
            return

        # Verificar comandos
        for cmd in ["libreoffice", "lp"]:
            if subprocess.call(["which", cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) != 0:
                raise EnvironmentError(f"{cmd} no está disponible en el sistema.")

        # Crear directorio
        output_dir = Path("outputs/pdf")
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_output = output_dir / f"converted_{timestamp}.pdf"

        # Convertir a PDF
        convert_cmd = [
            "libreoffice", "--headless",
            "--convert-to", "pdf",
            "--outdir", str(output_dir),
            str(temp_excel_path)
        ]
        result = subprocess.run(convert_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        if result.returncode != 0:
            raise RuntimeError(f"Error al convertir a PDF:\n{result.stderr.decode()}")

        generated_pdf = output_dir / Path(temp_excel_path).with_suffix('.pdf').name
        if not generated_pdf.exists():
            raise FileNotFoundError("No se encontró el PDF convertido.")

        generated_pdf.rename(pdf_output)

        # Comando de impresión con parámetros opcionales
        print_cmd = ["lp"]
        if printer_name:
            print_cmd += ["-d", printer_name]
        if copies > 1:
            print_cmd += ["-n", str(copies)]
        if isinstance(options, list):
            for opt in options:
                print_cmd += ["-o", opt]

        print_cmd.append(str(pdf_output))

        subprocess.run(print_cmd)
        messagebox.showinfo("Impresión", f"PDF generado y enviado a imprimir:\n{pdf_output.name}")
        return pdf_output

    except Exception as e:
        messagebox.showerror("Error", f"Error impresión en Linux:\n{e}")
