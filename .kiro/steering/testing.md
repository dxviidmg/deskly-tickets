# Testing

## Frameworks reales

- **Backend:** pytest + pytest-asyncio + httpx. Tests en `api/tests/`. Usan
  SQLite en memoria vía dependency override (no requieren Docker).
- **Frontend:** no hay framework de tests unitarios configurado. La verificación
  es `next lint` y el type-check del `next build`. **No inventar** Jest/Vitest/
  Playwright si la tarea no los introduce explícitamente.

## Reglas

- Ejecutar **primero los tests relacionados** con el cambio, no toda la suite.
  Ej: `pytest api/tests/test_state_machine.py -q`.
- Ejecutar la suite completa solo antes de cerrar una tarea o si el cambio es
  transversal.
- Verificar los **criterios de aceptación** de la spec, no solo que "pase verde".

## Lint / type checking

- **Backend:** `ruff check app tests` (config en `api/ruff.toml`).
- **Frontend:** `npm run lint`; type-check con `npx tsc --noEmit` o `next build`.
- Ejecutar lint/type-check cuando el cambio lo amerite (código nuevo o refactor),
  acotando la salida.

## Al añadir features/bugfixes

- Acompañar con test(s): al menos un caso válido y uno inválido para lógica de
  negocio (p. ej. transiciones de estado, firma del webhook).
