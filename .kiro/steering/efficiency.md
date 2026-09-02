# Eficiencia de contexto y tokens

Objetivo: hacer el trabajo leyendo y ejecutando lo mínimo necesario.

## Lectura

- Inspeccionar **solo** los archivos relevantes a la tarea. No analizar todo el
  repositorio "por si acaso".
- Preferir lectura por rango (offset/limit) o búsqueda dirigida sobre leer
  archivos completos. No releer un archivo ya visto en la sesión.
- **Nunca** leer directorios generados: `node_modules/`, `.next/`, `.venv/`,
  `__pycache__/`, `*.tsbuildinfo`, `dist/`, `build/`, `package-lock.json`.

## Ejecución

- Ejecutar solo los comandos que la tarea requiere. No repetir comandos ya
  ejecutados sin motivo.
- Acotar salidas: usar `--tail`, `-q`, filtros (`grep`), o límites. Evitar
  outputs enormes que inflan el contexto.
- Ver `docker.md` (no reconstruir/levantar Docker sin necesidad) y `testing.md`
  (ejecutar primero los tests relacionados, no toda la suite).

## Cambios

- Cambios pequeños y enfocados en el objetivo.
- No modificar archivos no relacionados con la tarea.
- No instalar dependencias sin justificación clara; si se añade una, fijar versión.
