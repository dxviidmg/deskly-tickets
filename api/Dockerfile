################################################################################
# ARCHIVO: api/Dockerfile
# PROPÓSITO: Imagen Docker del backend (FastAPI)
#
# Docker permite "empacar" la aplicación en una imagen que se puede
# ejecutar en cualquier máquina/servidor sin dependencias externas.
#
# Este Dockerfile usa multi-stage build:
# - Stage 1 (builder): compila wheels (binarios) de las dependencias
# - Stage 2 (runtime): imagen final pequeña, solo lo necesario para correr
#
# Ventajas del multi-stage:
# - Imagen final más pequeña (sin compilador de C, etc.)
# - Build cache: si no cambian dependencias, se reutiliza Stage 1
#
# Cómo se construye: docker build -t deskly-api:latest api/
# Cómo se ejecuta:    docker run -e DATABASE_URL=... deskly-api:latest
################################################################################

# syntax=docker/dockerfile:1

# ========== STAGE 1: Builder (compilar wheels) ==========
# Imagen: Python 3.12 slim (170MB, sin documentación, sin dev tools)
FROM python:3.12-slim AS builder

# No cachear pip (reduce tamaño de caché)
ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Copiar requirements.txt (no todo el código, para mejor cache)
COPY requirements.txt .

# Compilar wheels: esto permite instalar sin compilador en Stage 2
# pip wheel: genera .whl files (binarios precompilados de cada librería)
# Esto evita que Stage 2 tenga que compilar durante install
RUN pip wheel --wheel-dir /wheels -r requirements.txt


# ========== STAGE 2: Runtime (imagen final) ==========
# Imagen: Python 3.12 slim (limpia)
FROM python:3.12-slim AS runtime

# Variables de ambiente para Python
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Copiar wheels del stage anterior
COPY --from=builder /wheels /wheels
COPY requirements.txt .

# Instalar dependencias desde wheels (rápido, sin compilador)
# --no-index: solo desde wheels, no descargar de PyPI
# --find-links=/wheels: buscar paquetes en /wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt \
    && rm -rf /wheels

# Copiar código de la aplicación
COPY . .

# Asegurar que entrypoint.sh es ejecutable
# (a veces al clonar el repo en Windows pierden permisos)
RUN chmod +x entrypoint.sh

# Ejecutar como usuario no-root (seguridad: si hackean el contenedor,
# no tienen acceso root al host)
RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser

# Puerto que expone (informativo, no vincula automáticamente)
EXPOSE 8000

# Comando al arrancar: ejecutar entrypoint.sh
# El entrypoint.sh hace:
# 1. Aplicar migraciones (alembic upgrade head)
# 2. Arrancar uvicorn
ENTRYPOINT ["bash", "./entrypoint.sh"]
