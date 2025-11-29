#!/bin/bash

# 1. Activar entorno virtual (Ajusta la ruta si es distinta)
source venv/bin/activate

# 2. Ejecutar el script Python sin buffer
# Puedes agregar argumentos aquí si quieres (ej: --tipo cam)
python3 -u analisis_completo.py

# 3. Desactivar
deactivate