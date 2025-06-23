"""
Aplicación principal de Exelcior Apolo refactorizada.

Punto de entrada principal con arquitectura limpia y manejo robusto de errores.
"""

import sys
import threading
from pathlib import Path
from typing import Optional
import tkinter as tk
from tkinter import messagebox

# Añadir src al path para imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from exelcior.constants import APP_NAME, APP_VERSION, GUI_CONFIG
from exelcior.config import config_manager
from exelcior.database import database_manager
from exelcior.utils import get_logger, ExelciorError
from exelcior.gui.main_window import MainWindow

logger = get_logger("exelcior.main")


class ExelciorApplication:
    """
    Aplicación principal de Exelcior Apolo.
    
    Maneja la inicialización, configuración y ciclo de vida
    de la aplicación con arquitectura limpia.
    """

    def __init__(self):
        """Inicializa la aplicación."""
        self.root: Optional[tk.Tk] = None
        self.main_window: Optional[MainWindow] = None
        self._initialized = False

    def initialize(self) -> None:
        """Inicializa todos los componentes de la aplicación."""
        try:
            logger.info(f"Iniciando {APP_NAME} v{APP_VERSION}")
            
            # Configurar manejo global de excepciones
            self._setup_exception_handling()
            
            # Inicializar base de datos
            database_manager.initialize()
            logger.info("Base de datos inicializada")
            
            # Crear ventana principal
            self._create_main_window()
            
            # Configurar aplicación
            self._configure_application()
            
            self._initialized = True
            logger.info("Aplicación inicializada correctamente")
            
        except Exception as e:
            logger.critical(f"Error crítico en inicialización: {e}")
            self._show_critical_error(f"Error al inicializar aplicación: {str(e)}")
            sys.exit(1)

    def _setup_exception_handling(self) -> None:
        """Configura el manejo global de excepciones."""
        def handle_exception(exc_type, exc_value, exc_traceback):
            if issubclass(exc_type, KeyboardInterrupt):
                sys.__excepthook__(exc_type, exc_value, exc_traceback)
                return
            
            logger.critical(
                "Excepción no capturada",
                exc_info=(exc_type, exc_value, exc_traceback)
            )
            
            # Mostrar error al usuario si hay GUI
            if self.root:
                try:
                    messagebox.showerror(
                        "Error Crítico",
                        f"Se produjo un error inesperado:\n{exc_value}\n\n"
                        "La aplicación se cerrará. Revise los logs para más detalles."
                    )
                except:
                    pass  # GUI no disponible
        
        sys.excepthook = handle_exception

    def _create_main_window(self) -> None:
        """Crea la ventana principal de la aplicación."""
        self.root = tk.Tk()
        
        # Configuración básica de la ventana
        self.root.title(f"{APP_NAME} v{APP_VERSION}")
        self.root.geometry(GUI_CONFIG["window_size"])
        self.root.minsize(*GUI_CONFIG["min_window_size"])
        
        # Configurar tema
        try:
            from tkinter import ttk
            style = ttk.Style()
            style.theme_use(GUI_CONFIG["theme"])
        except Exception as e:
            logger.warning(f"No se pudo configurar tema: {e}")
        
        # Crear ventana principal
        self.main_window = MainWindow(self.root)

    def _configure_application(self) -> None:
        """Configura opciones adicionales de la aplicación."""
        # Configurar protocolo de cierre
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        # Configurar icono si existe
        icon_path = Path("assets/icon.ico")
        if icon_path.exists():
            try:
                self.root.iconbitmap(str(icon_path))
            except Exception as e:
                logger.warning(f"No se pudo cargar icono: {e}")

    def _on_closing(self) -> None:
        """Maneja el cierre de la aplicación."""
        try:
            logger.info("Cerrando aplicación...")
            
            # Guardar configuraciones
            config_manager.save_all_configs()
            
            # Cerrar ventana
            if self.root:
                self.root.quit()
                self.root.destroy()
                
        except Exception as e:
            logger.error(f"Error al cerrar aplicación: {e}")
        finally:
            sys.exit(0)

    def run(self) -> None:
        """Ejecuta la aplicación."""
        if not self._initialized:
            self.initialize()
        
        try:
            logger.info("Iniciando bucle principal de la aplicación")
            self.root.mainloop()
        except Exception as e:
            logger.critical(f"Error en bucle principal: {e}")
            self._show_critical_error(f"Error en ejecución: {str(e)}")
        finally:
            self._cleanup()

    def _cleanup(self) -> None:
        """Limpia recursos al finalizar."""
        try:
            logger.info("Limpiando recursos...")
            # Aquí se pueden añadir más operaciones de limpieza
        except Exception as e:
            logger.error(f"Error en limpieza: {e}")

    def _show_critical_error(self, message: str) -> None:
        """Muestra un error crítico al usuario."""
        try:
            # Intentar mostrar con tkinter
            root = tk.Tk()
            root.withdraw()  # Ocultar ventana principal
            messagebox.showerror("Error Crítico", message)
            root.destroy()
        except:
            # Fallback a print si GUI no está disponible
            print(f"ERROR CRÍTICO: {message}")


def main():
    """Función principal de entrada."""
    try:
        app = ExelciorApplication()
        app.run()
    except KeyboardInterrupt:
        logger.info("Aplicación interrumpida por usuario")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"Error fatal: {e}")
        print(f"Error fatal: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
