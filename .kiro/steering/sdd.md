# Spec-Driven Development (SDD)

Las specs viven en `docs/specs/`. La spec es la **fuente de verdad**.

## Flujo obligatorio

1. **Leer la spec primero.** Antes de tocar código, entender requisitos, diseño y
   tareas de la spec correspondiente. Si no hay spec para la funcionalidad nueva,
   crearla/actualizarla antes de implementar.
2. **Identificar archivos relevantes.** Localizar solo los módulos que la tarea
   toca (ver `efficiency.md`). No mapear todo el repo.
3. **Trabajar con criterios de aceptación.** Cada tarea se considera hecha cuando
   cumple los criterios de la spec, no antes.
4. **Implementar → probar → verificar.** Escribir el cambio, ejecutar los tests
   relacionados (ver `testing.md`), verificar los criterios.

## Límites

- **No implementar funcionalidades no solicitadas** por la spec.
- **No refactorizar código no relacionado** con la tarea actual.
- Si aparece un bug o mejora fuera de alcance, anotarlo, no arreglarlo dentro de
  la misma tarea (salvo que bloquee la spec).
- Ante ambigüedad entre spec y código, gana la spec; si la spec está mal,
  actualizar la spec primero.

## Registro

- Documentar decisiones relevantes en `DECISIONES.md`
  (Contexto / Uso de LLM / Salida del modelo / Mi decisión).
