"""
Sistema de impresión refactorizado para Exelcior Apolo.

Proporciona una interfaz unificada para diferentes tipos de impresión
con detección automática de plataforma y manejo robusto de errores.
"""

import platform
import socket
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Dict, Any, Union
from datetime import datetime

from ..constants import NETWORK_CONFIG, PRINT_CONFIG
from ..config import config_manager
from ..utils import get_logger, PrinterError, NetworkError
from ..database import database_manager

logger = get_logger("exelcior.printer")


class PrinterInterface(ABC):
    """Interfaz abstracta para diferentes tipos de impresoras."""

    @abstractmethod
    def print_document(self, file_path: Path, **kwargs) -> bool:
        """
        Imprime un documento.
        
        Args:
            file_path: Ruta del archivo a imprimir
            **kwargs: Argumentos adicionales específicos del printer
            
        Returns:
            True si la impresión fue exitosa
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        Verifica si la impresora está disponible.
        
        Returns:
            True si la impresora está disponible
        """
        pass


class SystemPrinter(PrinterInterface):
    """Impresora del sistema operativo."""

    def __init__(self, printer_name: Optional[str] = None):
        """
        Inicializa la impresora del sistema.
        
        Args:
            printer_name: Nombre específico de la impresora
        """
        self.printer_name = printer_name
        self.platform = platform.system()

    def print_document(self, file_path: Path, **kwargs) -> bool:
        """Imprime usando la impresora del sistema."""
        try:
            if self.platform == "Windows":
                return self._print_windows(file_path, **kwargs)
            elif self.platform == "Linux":
                return self._print_linux(file_path, **kwargs)
            else:
                raise PrinterError(f"Plataforma no soportada: {self.platform}")
                
        except Exception as e:
            logger.error(f"Error en impresión del sistema: {e}")
            return False

    def _print_windows(self, file_path: Path, **kwargs) -> bool:
        """Imprime en Windows usando win32print."""
        try:
            # Intentar importar win32print
            import win32print
            import win32api
            
            if self.printer_name:
                win32print.SetDefaultPrinter(self.printer_name)
            
            win32api.ShellExecute(0, "print", str(file_path), None, ".", 0)
            logger.info(f"Documento enviado a impresora Windows: {file_path}")
            return True
            
        except ImportError:
            logger.warning("win32print no disponible, usando método alternativo")
            return self._print_windows_alternative(file_path)
        except Exception as e:
            logger.error(f"Error en impresión Windows: {e}")
            return False

    def _print_windows_alternative(self, file_path: Path) -> bool:
        """Método alternativo de impresión para Windows."""
        try:
            cmd = ["print", f'"{file_path}"']
            if self.printer_name:
                cmd = ["print", f'/D:"{self.printer_name}"', f'"{file_path}"']
            
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            return result.returncode == 0
            
        except Exception as e:
            logger.error(f"Error en impresión alternativa Windows: {e}")
            return False

    def _print_linux(self, file_path: Path, **kwargs) -> bool:
        """Imprime en Linux usando lp."""
        try:
            cmd = ["lp"]
            
            if self.printer_name:
                cmd.extend(["-d", self.printer_name])
            
            # Opciones adicionales
            copies = kwargs.get("copies", 1)
            if copies > 1:
                cmd.extend(["-n", str(copies)])
            
            cmd.append(str(file_path))
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"Documento enviado a impresora Linux: {file_path}")
                return True
            else:
                logger.error(f"Error en lp: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error en impresión Linux: {e}")
            return False

    def is_available(self) -> bool:
        """Verifica si hay impresoras disponibles en el sistema."""
        try:
            if self.platform == "Windows":
                import win32print
                printers = win32print.EnumPrinters(2)
                return len(printers) > 0
            elif self.platform == "Linux":
                result = subprocess.run(["lpstat", "-p"], capture_output=True, text=True)
                return result.returncode == 0 and "printer" in result.stdout
            return False
        except:
            return False


class ZebraPrinter(PrinterInterface):
    """Impresora Zebra via TCP/IP."""

    def __init__(self, ip: Optional[str] = None, port: Optional[int] = None):
        """
        Inicializa la impresora Zebra.
        
        Args:
            ip: Dirección IP de la impresora
            port: Puerto de conexión
        """
        self.ip = ip or config_manager.network.zebra_ip
        self.port = port or config_manager.network.zebra_port
        self.timeout = config_manager.network.connection_timeout

    def print_document(self, file_path: Path, **kwargs) -> bool:
        """Imprime usando comandos ZPL."""
        try:
            # Para archivos ZPL, enviar directamente
            if file_path.suffix.lower() == '.zpl':
                return self._send_zpl_file(file_path)
            
            # Para otros archivos, generar ZPL básico
            zpl_content = self._generate_basic_zpl(file_path, **kwargs)
            return self._send_zpl_content(zpl_content)
            
        except Exception as e:
            logger.error(f"Error en impresión Zebra: {e}")
            return False

    def _send_zpl_file(self, file_path: Path) -> bool:
        """Envía un archivo ZPL directamente."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                zpl_content = f.read()
            return self._send_zpl_content(zpl_content)
        except Exception as e:
            logger.error(f"Error al leer archivo ZPL: {e}")
            return False

    def _send_zpl_content(self, zpl_content: str) -> bool:
        """Envía contenido ZPL a la impresora."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(self.timeout)
                sock.connect((self.ip, self.port))
                sock.send(zpl_content.encode('utf-8'))
                
            logger.info(f"ZPL enviado a Zebra {self.ip}:{self.port}")
            return True
            
        except socket.timeout:
            logger.error(f"Timeout conectando a Zebra {self.ip}:{self.port}")
            return False
        except socket.error as e:
            logger.error(f"Error de conexión Zebra: {e}")
            return False

    def _generate_basic_zpl(self, file_path: Path, **kwargs) -> str:
        """Genera ZPL básico para un archivo."""
        # ZPL básico para imprimir texto del nombre del archivo
        zpl = f"""
^XA
^FO50,50^A0N,30,30^FDArchivo: {file_path.name}^FS
^FO50,100^A0N,20,20^FDFecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}^FS
^XZ
"""
        return zpl

    def is_available(self) -> bool:
        """Verifica si la impresora Zebra está disponible."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(2)
                result = sock.connect_ex((self.ip, self.port))
                return result == 0
        except:
            return False


class PDFExporter:
    """Exportador de documentos a PDF."""

    def __init__(self):
        """Inicializa el exportador PDF."""
        self.output_dir = Path("exports/pdf")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export_dataframe(
        self, 
        df, 
        filename: Optional[str] = None,
        title: Optional[str] = None,
        **kwargs
    ) -> Path:
        """
        Exporta un DataFrame a PDF.
        
        Args:
            df: DataFrame a exportar
            filename: Nombre del archivo (sin extensión)
            title: Título del documento
            **kwargs: Opciones adicionales
            
        Returns:
            Ruta del archivo PDF generado
        """
        try:
            from fpdf import FPDF
            
            # Generar nombre de archivo si no se proporciona
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"export_{timestamp}"
            
            output_path = self.output_dir / f"{filename}.pdf"
            
            # Crear PDF
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=10)
            
            # Título
            if title:
                pdf.set_font("Arial", "B", 14)
                pdf.cell(0, 10, title, ln=True, align="C")
                pdf.ln(5)
                pdf.set_font("Arial", size=10)
            
            # Calcular ancho de columnas
            page_width = pdf.w - 2 * pdf.l_margin
            col_width = page_width / len(df.columns)
            
            # Encabezados
            pdf.set_font("Arial", "B", 10)
            pdf.set_fill_color(200, 200, 200)
            for col in df.columns:
                pdf.cell(col_width, 8, str(col), border=1, align="C", fill=True)
            pdf.ln()
            
            # Datos
            pdf.set_font("Arial", size=9)
            for _, row in df.iterrows():
                for value in row:
                    # Truncar texto largo
                    text = str(value)[:20] + "..." if len(str(value)) > 20 else str(value)
                    pdf.cell(col_width, 6, text, border=1, align="C")
                pdf.ln()
            
            # Pie de página
            pdf.ln(10)
            pdf.set_font("Arial", "I", 8)
            pdf.cell(0, 5, f"Generado el {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", align="C")
            
            # Guardar
            pdf.output(str(output_path))
            
            logger.info(f"PDF exportado: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error al exportar PDF: {e}")
            raise PrinterError(f"No se pudo exportar PDF: {str(e)}")


class PrintManager:
    """
    Gestor principal de impresión.
    
    Coordina diferentes tipos de impresoras y exportadores
    proporcionando una interfaz unificada.
    """

    def __init__(self):
        """Inicializa el gestor de impresión."""
        self.system_printer = SystemPrinter()
        self.zebra_printer = ZebraPrinter()
        self.pdf_exporter = PDFExporter()

    def print_dataframe(
        self,
        df,
        mode: str = "pdf",
        printer_name: Optional[str] = None,
        filename: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Imprime o exporta un DataFrame.
        
        Args:
            df: DataFrame a imprimir
            mode: Modo de impresión (pdf, system, zebra)
            printer_name: Nombre específico de impresora
            filename: Nombre del archivo para PDF
            **kwargs: Opciones adicionales
            
        Returns:
            Diccionario con resultado de la operación
        """
        start_time = datetime.now()
        
        try:
            if mode == "pdf":
                output_path = self.pdf_exporter.export_dataframe(
                    df, filename=filename, **kwargs
                )
                
                # Registrar en historial
                database_manager.save_print_history(
                    file_path=output_path,
                    print_type="PDF",
                    success=True
                )
                
                return {
                    "success": True,
                    "mode": "pdf",
                    "output_path": str(output_path),
                    "message": f"PDF generado: {output_path.name}"
                }
                
            elif mode == "system":
                # Primero exportar a PDF temporal
                temp_pdf = self.pdf_exporter.export_dataframe(df, filename="temp_print")
                
                # Imprimir PDF
                printer = SystemPrinter(printer_name)
                success = printer.print_document(temp_pdf, **kwargs)
                
                # Registrar en historial
                database_manager.save_print_history(
                    file_path=temp_pdf,
                    printer_name=printer_name,
                    print_type="System",
                    success=success
                )
                
                return {
                    "success": success,
                    "mode": "system",
                    "printer": printer_name,
                    "message": "Documento enviado a impresora" if success else "Error en impresión"
                }
                
            elif mode == "zebra":
                # Para Zebra, generar ZPL básico
                success = self.zebra_printer.print_document(Path("temp"), **kwargs)
                
                # Registrar en historial
                database_manager.save_print_history(
                    file_path="zebra_print",
                    printer_name=f"{self.zebra_printer.ip}:{self.zebra_printer.port}",
                    print_type="Zebra",
                    success=success
                )
                
                return {
                    "success": success,
                    "mode": "zebra",
                    "printer": f"{self.zebra_printer.ip}:{self.zebra_printer.port}",
                    "message": "Etiqueta enviada a Zebra" if success else "Error en impresión Zebra"
                }
                
            else:
                raise PrinterError(f"Modo de impresión no válido: {mode}")
                
        except Exception as e:
            logger.error(f"Error en impresión: {e}")
            return {
                "success": False,
                "mode": mode,
                "error": str(e),
                "message": f"Error: {str(e)}"
            }
        finally:
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"Operación de impresión completada en {processing_time:.2f}s")

    def get_available_printers(self) -> Dict[str, Any]:
        """
        Obtiene lista de impresoras disponibles.
        
        Returns:
            Diccionario con impresoras disponibles
        """
        result = {
            "system": {
                "available": self.system_printer.is_available(),
                "printers": []
            },
            "zebra": {
                "available": self.zebra_printer.is_available(),
                "ip": self.zebra_printer.ip,
                "port": self.zebra_printer.port
            }
        }
        
        # Obtener lista de impresoras del sistema
        try:
            if platform.system() == "Windows":
                import win32print
                printers = [printer[2] for printer in win32print.EnumPrinters(2)]
                result["system"]["printers"] = printers
            elif platform.system() == "Linux":
                proc = subprocess.run(["lpstat", "-p"], capture_output=True, text=True)
                if proc.returncode == 0:
                    lines = proc.stdout.split('\n')
                    printers = [line.split()[1] for line in lines if line.startswith("printer")]
                    result["system"]["printers"] = printers
        except Exception as e:
            logger.warning(f"No se pudieron obtener impresoras del sistema: {e}")
        
        return result

    def test_printer(self, printer_type: str, **kwargs) -> bool:
        """
        Prueba una impresora específica.
        
        Args:
            printer_type: Tipo de impresora (system, zebra)
            **kwargs: Argumentos específicos
            
        Returns:
            True si la prueba fue exitosa
        """
        try:
            if printer_type == "system":
                return self.system_printer.is_available()
            elif printer_type == "zebra":
                return self.zebra_printer.is_available()
            else:
                return False
        except Exception as e:
            logger.error(f"Error en prueba de impresora: {e}")
            return False


# Instancia global del gestor de impresión
print_manager = PrintManager()

