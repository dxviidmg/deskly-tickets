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

## Entorno de desarrollo (Opción A)

- `db` (PostgreSQL) y `redis` corren en Docker vía `docker-compose.override.yml`
  (db expuesta en el host en el puerto **5433**, redis en 6379). Ese override está
  en `.gitignore` (no se versiona).
- Backend: local con `uvicorn app.main:app --reload` (venv Python 3.12 en
  `api/.venv`, gestionado con `uv`). Vars: `DATABASE_URL=...@localhost:5433/deskly`.
- Frontend: local con `npm run dev`.
- Credenciales del seed: `admin@deskly.com` / `admin123` (admin),
  `agente@deskly.com` / `agente123` (agente).
