#!/usr/bin/env python3
"""
Punto de entrada principal para Exelcior Apolo Dashboard
"""

import sys
import logging
from pathlib import Path

# Agregar el directorio src al path
src_dir = Path(__file__).parent
sys.path.insert(0, str(src_dir))

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    """Función principal"""
    try:
        from exelcior.gui.dashboard import ExelciorDashboard
        
        # Crear y ejecutar aplicación
        app = ExelciorDashboard()
        app.mainloop()
        
    except ImportError as e:
        print(f"Error de importación: {e}")
        print("Asegúrese de que todas las dependencias estén instaladas.")
        sys.exit(1)
    except Exception as e:
        print(f"Error inesperado: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

