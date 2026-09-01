################################################################################
# ARCHIVO: web/Dockerfile
# PROPÓSITO: Imagen Docker del frontend (Next.js)
#
# Next.js es un framework React que permite renderizar en servidor (SSR)
# y generar sitios estáticos. Este Dockerfile optimiza el build y runtime.
#
# Multi-stage build:
# - Stage 1 (deps): instala dependencias de npm
# - Stage 2 (builder): construye la aplicación Next.js
# - Stage 3 (runtime): imagen final solo con lo necesario para servir
#
# Ventajas:
# - La imagen final es ~150MB (vs ~600MB si incluyera todo)
# - Build cache: si no cambian node_modules, no se reinstalan
#
# Cómo se construye: docker build web/
# Con argumentos:     docker build --build-arg NEXT_PUBLIC_API_URL=https://api.example.com web/
################################################################################

# syntax=docker/dockerfile:1

# ========== STAGE 1: Instalación de dependencias ==========
# Imagen: Node.js 22 alpine (~200MB, muy ligera)
FROM node:22-alpine AS deps

WORKDIR /app

# Copiar archivos de lockfile
COPY package.json package-lock.json ./

# npm ci (clean install): instala exactamente las versiones del package-lock.json
# (diferencia de "npm install" que puede instalar versiones nuevas)
# Determinístico: mismos node_modules en dev, ci, producción
RUN npm ci


# ========== STAGE 2: Construcción ==========
# Imagen: Node.js 22 alpine
FROM node:22-alpine AS builder

WORKDIR /app

# Copiar node_modules del stage anterior (evita reinstalar)
COPY --from=deps /app/node_modules ./node_modules

# Copiar todo el código fuente
COPY . .

# Argumentos de build: URLs que se "hornean" en el JavaScript
# Estos valores se reemplazan en tiempo de build (no runtime)
# El navegador los usará para conectar al API
ARG NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_WS_URL

# Establecer variables de entorno para el build
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL \
    NEXT_PUBLIC_WS_URL=$NEXT_PUBLIC_WS_URL \
    NEXT_TELEMETRY_DISABLED=1

# Ejecutar build: "npm run build" genera:
# - .next/: carpeta con aplicación compilada y optimizada
# - .next/static/: archivos estáticos (CSS, JS, imágenes)
RUN npm run build


# ========== STAGE 3: Runtime (imagen final) ==========
# Imagen: Node.js 22 alpine (limpia)
FROM node:22-alpine AS runtime

WORKDIR /app

# Variables de entorno
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1

# Copiar solo lo necesario para ejecutar Next.js
# NO copiamos node_modules completo, solo src files
COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/next.config.js ./next.config.js

# Puerto que expone
EXPOSE 3000

# Comando al arrancar: "npm start" = "next start"
# Inicia Next.js en modo producción
CMD ["npm", "run", "start"]
