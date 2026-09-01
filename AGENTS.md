# Reglas de trabajo — Deskly

Estas reglas aplican SIEMPRE en este repositorio, en cualquier sesión.

## Eficiencia (modo económico)

1. **Reducir verificaciones al mínimo.** Confía en el hot reload del entorno de
   desarrollo (frontend en :3000, backend en :8000 con `--reload`). El usuario ve
   los cambios en vivo, así que no hace falta verificar cada cambio.

2. **Lecturas por rango, no archivos completos.** Usa `grep` o lectura con
   offset/limit. No releas un archivo que ya viste en la sesión.

3. **No compilar ni ejecutar tests automáticamente.** NO ejecutar `npm run build`,
   `next build`, `tsc`, `pytest`, `docker build`, `docker compose up`, ni ninguna
   compilación o suite de tests **a menos que el usuario lo pida explícitamente**.
   Hacer los cambios de código y dejar que el usuario compruebe en pantalla.

4. **Salidas de comandos acotadas** cuando se ejecuten comandos (usar `tail`,
   `-q`, etc.) para no inflar el contexto.

## Metodología

- Se trabaja con **SDD (Spec-Driven Development)**: antes de implementar una
  funcionalidad nueva, actualizar la spec en `docs/specs/` (requisitos + diseño +
  tarea). El código va después de la spec.
- Documentar cada decisión relevante en `DECISIONES.md` con el formato
  `### [Decisión] Título` (Contexto / Uso de LLM / Salida del modelo / Mi decisión).
- Código en inglés; documentación en español.
- Commits atómicos con mensajes descriptivos (se hacen cuando el usuario lo pide).

## Documentación (REGLA OBLIGATORIA para todo código nuevo)

**TODO nuevo código (features, bugfixes, refactoring) DEBE incluir documentación
según la guía `GUIA_DOCUMENTACION.md`.**

### Backend (Python)
- Encabezado de archivo: `MÓDULO:` + propósito + conceptos clave
- Cada función/clase: docstring con descripción, Args, Returns, Raises, Ejemplo
- Comentarios explicativos para lógica compleja
- Todos los comentarios en ESPAÑOL

### Frontend (TypeScript/React)
- Encabezado JSDoc explicando propósito del archivo
- Componentes/hooks con JSDoc: qué hacen, props, ejemplos
- Comentarios en ESPAÑOL explicando lógica no obvia
- Mensajes de error en ESPAÑOL

### DevOps/Config (Docker, CI/CD, etc.)
- Encabezado explicando propósito
- Cada sección comentada
- Variables documentadas
- Decisiones justificadas (por qué Docker, por qué este tamaño, etc.)

### Estándares aplicables a TODO
- ✅ Escribe como para alguien sin experiencia en esa tech
- ✅ Explica conceptos clave la primera vez (qué es ORM, qué es async, etc.)
- ✅ Incluye ejemplos reales de uso
- ✅ Explica por qué (no solo qué)
- ❌ NO comentarios obvios ("i = 0 // establecer i a 0")
- ❌ NO comentarios sin contexto
- ❌ NO documentación en inglés

**Referencia:** Ver `GUIA_DOCUMENTACION.md` para ejemplos, anti-patrones y checklist completo.

## Entorno de desarrollo (Opción A)

- `db` (PostgreSQL) y `redis` corren en Docker vía `docker-compose.override.yml`
  (db expuesta en el host en el puerto **5433**, redis en 6379). Ese override está
  en `.gitignore` (no se versiona).
- Backend: local con `uvicorn app.main:app --reload` (venv Python 3.12 en
  `api/.venv`, gestionado con `uv`). Vars: `DATABASE_URL=...@localhost:5433/deskly`.
- Frontend: local con `npm run dev`.
- Credenciales del seed: `admin@deskly.com` / `admin123` (admin),
  `agente@deskly.com` / `agente123` (agente).
