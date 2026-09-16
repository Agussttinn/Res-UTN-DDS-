#!/usr/bin/env bash
# Levanta backend (Django), mock de SysAcad (Node) y frontend (Angular)
# en simultáneo, con un solo comando. Ctrl+C corta los tres juntos.
#
# Uso: ./dev.sh

set -u

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colores para distinguir la salida de cada proceso
COLOR_BACK='\033[0;34m'   # azul
COLOR_MOCK='\033[0;33m'   # amarillo
COLOR_FRONT='\033[0;32m'  # verde
COLOR_RESET='\033[0m'

# Corre un comando y le agrega un prefijo de color a cada línea que imprime
run_prefixed() {
    local color="$1" label="$2"
    shift 2
    "$@" 2>&1 | while IFS= read -r line; do
        printf "${color}[%s]${COLOR_RESET} %s\n" "$label" "$line"
    done
}

cleanup() {
    echo ""
    echo "Deteniendo backend, mock-sysacad y frontend..."
    kill 0 2>/dev/null
}
trap cleanup EXIT INT TERM

if [ ! -x "$ROOT_DIR/backend/DSWenv/bin/python" ]; then
    echo "No encontré el entorno virtual en backend/DSWenv/."
    echo "Creálo primero: cd backend && python3 -m venv DSWenv && source DSWenv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Backend Django (uso el python del venv directo, sin necesidad de "activate")
run_prefixed "$COLOR_BACK" BACKEND \
    "$ROOT_DIR/backend/DSWenv/bin/python" "$ROOT_DIR/backend/manage.py" runserver &

# Mock de SysAcad
run_prefixed "$COLOR_MOCK" MOCK \
    bash -c "cd '$ROOT_DIR/backend/core/mock-sysacad' && npm run dev" &

# Frontend Angular
run_prefixed "$COLOR_FRONT" FRONTEND \
    bash -c "cd '$ROOT_DIR/frontend' && npm start" &

wait
