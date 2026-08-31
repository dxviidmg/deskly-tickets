# Requisitos — Deskly

Sistema de tickets de soporte. Este documento recoge las historias de usuario y
sus criterios de aceptación. Los criterios se redactan con el patrón EARS
(Easy Approach to Requirements Syntax): "Cuando <evento/condición>, el sistema
deberá <respuesta esperada>".

El alcance obligatorio proviene del enunciado del desafío. Los puntos marcados
como *(bonus)* no son obligatorios y se implementarán solo si queda tiempo.

---

## 1. Gestión de tickets (CRUD)

**Historia:** Como agente de soporte quiero registrar y gestionar tickets para
dar seguimiento a las incidencias de los clientes.

Criterios de aceptación:

1. Cuando un cliente envía `POST /api/tickets` con un cuerpo válido, el sistema
   deberá crear el ticket con estado inicial `abierto` y devolver `201` con el
   recurso creado, incluyendo `id`, `creado_en` y `actualizado_en`.
2. Cuando un cliente envía `POST /api/tickets` con un cuerpo inválido (campos
   faltantes o tipos incorrectos), el sistema deberá devolver `422` con el
   detalle de los errores de validación.
3. Cuando un cliente solicita `GET /api/tickets`, el sistema deberá devolver una
   lista paginada de tickets con metadatos de paginación (total, página, tamaño).
4. Cuando un cliente solicita `GET /api/tickets` con el parámetro `estado` o
   `prioridad`, el sistema deberá devolver solo los tickets que coincidan con el
   filtro.
5. Cuando un cliente solicita `GET /api/tickets/{id}` de un ticket existente, el
   sistema deberá devolver `200` con el detalle del ticket.
6. Cuando un cliente solicita `GET /api/tickets/{id}` de un ticket inexistente,
   el sistema deberá devolver `404` con un mensaje claro.
7. Cuando un cliente envía `PATCH /api/tickets/{id}` con campos válidos, el
   sistema deberá actualizar solo los campos provistos y refrescar
   `actualizado_en`.

---

## 2. Máquina de estados

**Historia:** Como agente quiero que el ciclo de vida del ticket esté controlado
para evitar transiciones inconsistentes.

Estados: `abierto`, `en_progreso`, `resuelto`, `cerrado`.

Transiciones válidas:

- `abierto → en_progreso`
- `en_progreso → resuelto`
- `resuelto → cerrado`
- `resuelto → abierto` (reabierto)

Criterios de aceptación:

1. Cuando un agente envía `POST /api/tickets/{id}/transicion` con una transición
   válida, el sistema deberá actualizar el estado, refrescar `actualizado_en` y
   devolver `200` con el ticket actualizado.
2. Cuando un agente solicita una transición inválida (p. ej. `abierto → cerrado`),
   el sistema deberá devolver `409 Conflict` con un mensaje que indique el estado
   actual, el estado solicitado y las transiciones permitidas. **No** deberá
   devolver un `500` genérico.
3. Cuando un agente solicita una transición sobre un ticket inexistente, el
   sistema deberá devolver `404`.

---

## 3. Comentarios

**Historia:** Como agente quiero comentar en un ticket para dejar constancia del
avance.

Criterios de aceptación:

1. Cuando un agente envía `POST /api/tickets/{id}/comentarios` con un cuerpo
   válido, el sistema deberá crear el comentario asociado al ticket y devolver
   `201`.
2. Cuando se consulta el detalle de un ticket, el sistema deberá poder exponer su
   hilo de comentarios ordenados cronológicamente.
3. Cuando se comenta sobre un ticket inexistente, el sistema deberá devolver `404`.

---

## 4. Webhook de ingesta

**Historia:** Como sistema externo quiero crear tickets en Deskly de forma segura
mediante un webhook firmado.

Criterios de aceptación:

1. Cuando llega `POST /api/webhooks/tickets` con una firma HMAC-SHA256 válida en
   el header `X-Signature` y un payload correcto, el sistema deberá crear el
   ticket y devolver `201`.
2. Cuando la firma es inválida o falta el header, el sistema deberá devolver
   `401` sin crear el ticket.
3. Cuando la firma es válida pero el payload está malformado, el sistema deberá
   devolver `422`.
4. La verificación de firma deberá usar comparación en tiempo constante
   (`hmac.compare_digest`) sobre el cuerpo crudo de la petición.
5. *(Bonus)* Cuando llega un `event_id` ya procesado, el sistema no deberá crear
   un ticket duplicado (idempotencia).
6. *(Bonus)* Cuando el `timestamp` de la petición es demasiado viejo, el sistema
   deberá rechazarla (protección contra replay).

---

## 5. WebSocket en tiempo real

**Historia:** Como agente conectado quiero ver los cambios de tickets en vivo sin
recargar la página.

Criterios de aceptación:

1. Cuando un cliente se conecta a `WS /ws/tickets`, el sistema deberá aceptar la
   conexión y mantenerla activa.
2. Cuando se crea, actualiza o comenta un ticket, el sistema deberá emitir a los
   clientes conectados un evento con `tipo` (`ticket.creado`,
   `ticket.actualizado`, `ticket.comentado`) y los datos del ticket afectado.
3. Cuando un cliente se desconecta, el sistema deberá dejar de enviarle mensajes
   y eliminarlo del registro sin lanzar errores silenciosos.

---

## 6. Frontend

**Historia:** Como agente quiero una interfaz para ver y gestionar tickets.

Criterios de aceptación:

1. Cuando el agente abre `/`, el sistema deberá mostrar una tabla paginada de
   tickets con al menos un filtro funcional.
2. La UI deberá diferenciar visualmente los estados de **carga**, **vacío** (sin
   tickets) y **error**. No deberá usarse el mismo indicador para todos.
3. Cuando el agente abre `/tickets/[id]`, el sistema deberá renderizar el detalle
   en el servidor (SSR), mostrando el hilo de comentarios y botones para cambiar
   de estado.
4. La UI deberá conectarse por WebSocket y actualizarse en vivo sin recargar,
   mediante un hook propio (`useTicketStream`) con limpieza correcta en
   `useEffect`.
5. La UI deberá mostrar un indicador visible del estado de conexión (conectado /
   desconectado).

---

## 7. Infraestructura y calidad

Criterios de aceptación:

1. El proyecto deberá arrancar con `git clone`, `cp .env.example .env` y
   `docker compose up --build`, levantando backend, frontend y base de datos.
2. No deberá haber secretos versionados; toda configuración sensible vendrá de
   `.env`.
3. Deberá existir al menos un índice de base de datos justificado en el README.
4. Deberán existir tests unitarios: transición válida e inválida de la máquina de
   estados, y firma válida e inválida del webhook.
