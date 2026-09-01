#!/usr/bin/env bash
###############################################################################
# ARCHIVO: dev-web.sh
# PROPÓSITO: (Modo B) Arrancar el frontend Next.js en LOCAL con recarga en vivo.
#
# El frontend habla con el backend por HTTP. En modo local el backend está en
# localhost:8000, que es el valor por defecto de NEXT_PUBLIC_API_URL y
# API_INTERNAL_URL en desarrollo, así que no hace falta configuración extra.
#
# REQUISITOS:
#   - Tener el backend corriendo (./dev-api.sh) para que las peticiones funcionen
#
# USO:
#   ./dev-web.sh
###############################################################################

set -euo pipefail

# Movernos al directorio del frontend.
cd "$(dirname "$0")/web"

# Instalar dependencias si aún no existen (primera vez).
if [[ ! -d node_modules ]]; then
  echo "node_modules no encontrado; instalando dependencias..."
  npm install
fi

echo "Frontend local en http://localhost:3000 (API en http://localhost:8000)"
# npm run dev arranca Next.js en modo desarrollo con hot reload.
exec npm run dev
