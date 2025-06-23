#!/bin/bash
# Exelcior Apolo v2.0.0 - Script de inicio para Linux
# Desarrollado por Gian Lucas San Martín - GCNJ

echo "========================================"
echo "   Exelcior Apolo v2.0.0"
echo "   Transformador Inteligente de Excel"
echo "========================================"
echo

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Función para mostrar errores
show_error() {
    echo -e "${RED}ERROR: $1${NC}"
}

# Función para mostrar éxito
show_success() {
    echo -e "${GREEN}$1${NC}"
}

# Función para mostrar advertencias
show_warning() {
    echo -e "${YELLOW}$1${NC}"
}

# Verificar si Python está instalado
if ! command -v python3 &> /dev/null; then
    show_error "Python 3 no está instalado"
    echo "Por favor instale Python 3.8 o superior:"
    echo "  Ubuntu/Debian: sudo apt install python3 python3-pip python3-venv"
    echo "  CentOS/RHEL: sudo yum install python3 python3-pip"
    exit 1
fi

# Verificar versión de Python
python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
required_version="3.8"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    show_error "Se requiere Python $required_version o superior. Versión actual: $python_version"
    exit 1
fi

# Verificar si estamos en el directorio correcto
if [ ! -f "src/main.py" ]; then
    show_error "No se encuentra el archivo src/main.py"
    echo "Asegúrese de ejecutar este script desde el directorio raíz del proyecto"
    exit 1
fi

# Crear entorno virtual si no existe
if [ ! -d "venv" ]; then
    echo "Creando entorno virtual..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        show_error "No se pudo crear el entorno virtual"
        echo "Intente instalar python3-venv:"
        echo "  Ubuntu/Debian: sudo apt install python3-venv"
        exit 1
    fi
    show_success "Entorno virtual creado"
fi

# Activar entorno virtual
echo "Activando entorno virtual..."
source venv/bin/activate

# Verificar si pip está disponible
if ! command -v pip &> /dev/null; then
    show_error "pip no está disponible en el entorno virtual"
    exit 1
fi

# Instalar dependencias si es necesario
if [ ! -d "venv/lib/python*/site-packages/pandas" ]; then
    echo "Instalando dependencias..."
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        show_error "No se pudieron instalar las dependencias"
        exit 1
    fi
    show_success "Dependencias instaladas"
fi

# Crear directorios necesarios
mkdir -p logs exports/pdf data/samples config

# Verificar dependencias del sistema para GUI
if ! python3 -c "import tkinter" 2>/dev/null; then
    show_warning "tkinter no está disponible"
    echo "Para usar la interfaz gráfica, instale tkinter:"
    echo "  Ubuntu/Debian: sudo apt install python3-tk"
    echo "  CentOS/RHEL: sudo yum install tkinter"
    echo
    read -p "¿Desea continuar sin GUI? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo
echo "Iniciando Exelcior Apolo..."
echo

# Ejecutar aplicación
python3 src/main.py

# Verificar código de salida
exit_code=$?
if [ $exit_code -ne 0 ]; then
    echo
    show_error "La aplicación se cerró con errores (código: $exit_code)"
    echo "Revise los logs en el directorio 'logs'"
    exit $exit_code
fi

echo
show_success "Gracias por usar Exelcior Apolo v2.0.0"

