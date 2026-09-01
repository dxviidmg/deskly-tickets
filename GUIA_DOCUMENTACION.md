# 📚 GUÍA DETALLADA DE DOCUMENTACIÓN - Deskly

Este documento es la **referencia completa** para documentar código.  
Para reglas rápidas, ver sección correspondiente en `AGENTS.md`.

**Aplicable a:**
- Backend (Python)
- Frontend (TypeScript/React)
- DevOps/Config (Docker, CI/CD, etc.)

---

## FILOSOFÍA

"Escribe como si documentaras para alguien que entra por primera vez al proyecto."

- ✅ Explica conceptos clave (ORM, async/await, componentes, etc.)
- ✅ Da ejemplos reales
- ✅ Explica el POR QUÉ, no solo el QUÉ
- ❌ No asumas experiencia técnica
- ❌ No hagas comentarios obvios
- ❌ No escribas en inglés

---

## 1. ARCHIVOS PYTHON (Backend)

### Encabezado del archivo
```python
"""
MÓDULO: app/repositories/ticket.py - Descripción

Explicación de qué hace este módulo.
Conceptos clave usados aquí.
Relaciones con otros módulos.
Ejemplo de uso típico.
"""
```

### Clases
```python
class TicketRepository:
    """
    Descripción en una línea.
    
    Párrafo explicativo: qué es, por qué existe, cuándo se usa.
    
    Métodos principales:
    - create: Crear nuevo ticket
    - update: Actualizar ticket existente
    - transition: Cambiar estado (valida máquina de estados)
    
    Ejemplo:
        repo = TicketRepository(session)
        ticket = await repo.create(TicketCreate(...))
    """
```

### Funciones/Métodos
```python
async def get_ticket(ticket_id: int) -> TicketDetail:
    """
    Obtiene un ticket con todos sus detalles.
    
    ¿Qué es "detalles"?
    Incluye comentarios e historial de cambios, no solo el ticket base.
    
    Args:
        ticket_id: ID único del ticket
        
    Returns:
        TicketDetail: Ticket con comentarios y state_log
        
    Raises:
        HTTPException(404): Si el ticket no existe
        
    Ejemplo:
        ticket = await get_ticket(5)
        # Devuelve:
        # {
        #   "id": 5,
        #   "titulo": "...",
        #   "comments": [...],
        #   "state_log": [...]
        # }
    """
```

### Secciones complejas
```python
# ========== CONCEPTO: Máquina de Estados ==========
# Define qué transiciones de estado son válidas.
# Ejemplo:
#   abierto → en_progreso ✓ (permitido)
#   cerrado → abierto ✗ (no permitido)
#
# ¿Por qué?
# - Evita cambios inválidos (ticket cerrado no puede volver a abierto)
# - Centraliza lógica de negocio
# - Fácil de testear y cambiar reglas
```

---

## 2. ARCHIVOS TYPESCRIPT/REACT (Frontend)

### Encabezado del archivo
```typescript
/**
 * ARCHIVO: components/TicketCard.tsx
 * PROPÓSITO: Renderiza una tarjeta individual de ticket
 *
 * Qué hace: muestra titulo, estado, prioridad, etc.
 * Cuándo se usa: en listas de tickets, en dashboard
 * Props: ticket, onUpdate, loading
 * Estado: none (componente "pure", sin estado local)
 */
```

### Componentes
```typescript
/**
 * TicketCard: tarjeta de un ticket individual.
 * 
 * Props:
 *   - ticket: Objeto TicketOut con datos
 *   - onUpdate: Callback cuando se actualiza (opcional)
 *   - loading: Si está cargando (por defecto false)
 *
 * Renderiza:
 *   - Título del ticket
 *   - Estado (badge con color)
 *   - Prioridad (icono)
 *   - Fecha de creación
 *   - Botón para ver detalles
 *
 * Ejemplo:
 *   <TicketCard
 *     ticket={ticket}
 *     onUpdate={(updated) => setTicket(updated)}
 *     loading={isSaving}
 *   />
 */
export function TicketCard({ ticket, onUpdate, loading = false }: Props) {
  // ...
}
```

### Hooks personalizados
```typescript
/**
 * useTicketStream: conecta a WebSocket y sincroniza tickets.
 *
 * Qué hace:
 * 1. Conecta a ws://localhost:8000/ws/tickets
 * 2. Escucha eventos (ticket.creado, ticket.actualizado, etc.)
 * 3. Cuando llega evento: actualiza React Query cache
 * 4. Si desconecta: intenta reconectar automáticamente
 * 5. Si reconecta: notifica al usuario
 *
 * ¿Por qué es importante?
 * Sin esto, los datos en pantalla serían stale (no verías cambios en tiempo real).
 *
 * Returns:
 *   {
 *     isConnected: boolean - si está conectado a WebSocket
 *     error: null | string - error si algo falló
 *     reconnect: () => void - forzar reconexión
 *   }
 *
 * Ejemplo:
 *   const { isConnected, error } = useTicketStream();
 *   return isConnected ? "🟢 Conectado" : "🔴 Desconectado";
 */
export function useTicketStream() {
  // ...
}
```

### Lógica compleja
```typescript
// Cuando el usuario crea un ticket:
// 1. Se envía al API (POST /api/tickets)
// 2. El API publica evento vía WebSocket (ticket.creado)
// 3. El backend propaga evento a todos los clientes conectados
// 4. useTicketStream() recibe evento
// 5. React Query cache se actualiza
// 6. Componentes que usan ese hook se re-renderizan
// 7. El nuevo ticket aparece en el dashboard sin refresh

async function handleCreateTicket() {
  try {
    // Crear ticket en BD
    const newTicket = await api.createTicket(form);
    // No necesitamos actualizar manualmente el cache
    // porque el WebSocket lo hará automáticamente
    // (cuando el servidor publica ticket.creado)
  } catch (error) {
    showError("No se pudo crear el ticket");
  }
}
```

---

## 3. ARCHIVOS DEVOPS/CONFIG

### Encabezado
```yaml
################################################################################
# ARCHIVO: docker-compose.yml
# PROPÓSITO: Orquestación de 4 servicios (db, redis, api, web)
#
# ¿Qué hace?
# Define cómo arrancar todos los servicios juntos en Docker.
# Especifica dependencias, volúmenes, networking, healthchecks.
#
# ¿Cuándo se usa?
# docker compose up --build    (arrancar todo)
# docker compose down          (parar todo)
# docker compose logs -f api   (ver logs)
#
# ¿Qué es docker-compose?
# Tool que permite definir múltiples contenedores y sus relaciones
# en un archivo YAML. Mucho más fácil que iniciar contenedores manualmente.
################################################################################
```

### Servicios
```yaml
services:
  # ========== POSTGRESQL 16 ==========
  # Base de datos relacional que almacena:
  # - Usuarios (agentes y administradores)
  # - Tickets (problemas reportados)
  # - Comentarios (progreso del ticket)
  # - Otros datos estructurados
  #
  # ¿Alpine?
  # Versión minimizada de Linux (~50MB vs 300MB normal).
  # Menos seguro, pero para desarrollo está bien.
  db:
    image: postgres:16-alpine
    
    # Volumen persistente: datos sobreviven si para/reinicia el contenedor
    # Sin esto: cada "docker compose up" estaría con BD vacía
    volumes:
      - db_data:/var/lib/postgresql/data
```

### Scripts
```bash
#!/usr/bin/env bash
# ARCHIVO: api/entrypoint.sh
# PROPÓSITO: Script que se ejecuta al arrancar el contenedor

# ¿Por qué es necesario?
# Docker inicia el contenedor pero PostgreSQL podría no estar listo.
# Este script:
# 1. Espera a que PostgreSQL responda (con reintentos)
# 2. Aplica migraciones de BD
# 3. Arranca el servidor

# set -euo pipefail:
# -e: salir si hay error
# -u: error si usa variable indefinida
# -o pipefail: error si falla comando en pipe
set -euo pipefail

# Reintentar hasta 10 veces (con esperas de 2s entre intentos)
for attempt in 1 2 3 4 5 6 7 8 9 10; do
  if alembic upgrade head; then
    echo "Migraciones aplicadas"
    break
  fi
  sleep 2
done

# exec: reemplaza este proceso con uvicorn
# (uvicorn recibe signals de Docker, etc.)
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## 4. ANTI-PATRONES: LO QUE NO HACER

### ❌ Comentarios obvios
```python
# MAL
i = 0  # Establecer i a 0
user_count = 0  # Contador de usuarios
x = x + 1  # Incrementar x

# BIEN
i = 0  # Inicializar contador para iterar sobre array
user_count = 0  # Almacenar total de usuarios registrados
active_sessions = active_sessions + 1  # Contar nueva sesión activa
```

### ❌ Sin contexto
```python
# MAL
if status == "pending" and days > 7:
    send_email()

# BIEN
# Enviar recordatorio si ticket está pendiente más de 7 días
# (mejora experiencia del cliente: ticket no queda olvidado)
if status == "pending" and days > 7:
    send_email()
```

### ❌ Documentación en inglés
```python
# MAL
async def get_user(user_id: int) -> User:
    # Fetch user from database or raise 404
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user

# BIEN
async def get_user(user_id: int) -> User:
    """
    Obtiene un usuario por ID.
    
    Si no existe: lanza HTTPException(404).
    """
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return user
```

### ❌ Sin ejemplos
```python
# MAL
async def create_ticket(title: str, description: str) -> Ticket:
    """Crea un ticket."""
    # ...

# BIEN
async def create_ticket(title: str, description: str) -> Ticket:
    """
    Crea un nuevo ticket.
    
    El ticket inicia en estado 'abierto' y se puede asignar después.
    
    Args:
        title: Asunto del ticket (1-200 caracteres)
        description: Descripción del problema
        
    Returns:
        Ticket creado (con id, estado, fechas)
        
    Ejemplo:
        ticket = await create_ticket(
            title="Error de login",
            description="No puedo entrar a la app"
        )
        # Resultado: Ticket(id=42, estado="abierto", ...)
    """
    # ...
```

---

## 5. CHECKLIST ANTES DE HACER PUSH

Verifica estos puntos para TODO código nuevo:

### Backend (Python)
- [ ] Archivo tiene encabezado con MÓDULO, PROPÓSITO, conceptos
- [ ] Cada función tiene docstring con descripción, Args, Returns, Raises, Ejemplo
- [ ] Lógica compleja está comentada paso a paso
- [ ] Conceptos clave están explicados (qué es, por qué, cuándo)
- [ ] Todos los comentarios en ESPAÑOL
- [ ] Sin comentarios obvios ("i = 0")
- [ ] Mensajes de error en ESPAÑOL

### Frontend (TypeScript/React)
- [ ] Archivo tiene encabezado JSDoc con ARCHIVO, PROPÓSITO
- [ ] Componentes/hooks tienen JSDoc: qué hacen, props, returns, ejemplo
- [ ] Lógica no obvia está comentada
- [ ] Todos los comentarios en ESPAÑOL
- [ ] Mensajes de error en ESPAÑOL
- [ ] Ejemplos de uso incluidos

### DevOps/Config
- [ ] Encabezado explica propósito
- [ ] Cada sección principal está comentada
- [ ] Variables están documentadas
- [ ] Se explica el POR QUÉ (por qué Docker, por qué este size, etc.)
- [ ] Pasos complejos están numerados y explicados

---

## 6. EJEMPLOS REALES DEL PROYECTO

Ver estos archivos como referencia:

**Backend:**
- `/home/david/deskly-tickets/api/app/main.py` - FastAPI setup, lifespan, middlewares
- `/home/david/deskly-tickets/api/app/models.py` - ORM models con relaciones
- `/home/david/deskly-tickets/api/app/routers/tickets.py` - REST endpoints
- `/home/david/deskly-tickets/api/app/repositories/ticket.py` - Repository pattern

**Frontend:**
- (Próximamente: web/components/TicketCard.tsx, web/hooks/useTicketStream.ts, etc.)

**DevOps:**
- `/home/david/deskly-tickets/docker-compose.yml` - Orquestación
- `/home/david/deskly-tickets/api/Dockerfile` - Multi-stage build
- `/home/david/deskly-tickets/api/entrypoint.sh` - Scripts de inicio
- `/home/david/deskly-tickets/.github/workflows/ci.yml` - CI/CD pipeline

---

## 7. PREGUNTAS FRECUENTES

**P: ¿Cuánto es "demasiado" documentar?**  
R: Si alguien sin experiencia en la tech entendería el código, es suficiente. Si no, agrega más.

**P: ¿Debo documentar código obvio?**  
R: Solo si el POR QUÉ es importante. Ejemplo: `if len(queue) > 100: stop_processing()` → NO es obvio por qué 100, documenta.

**P: ¿Qué si cambia código pero se olvida actualizar comentario?**  
R: En code review, si ves comentario desactualizado, pide que lo actualice.

**P: ¿Ejemplos al final del docstring o en archivos separados?**  
R: En docstring si es corto (1-5 líneas). Archivo separado en `docs/examples/` si es complejo.

---

## 📞 REFERENCIAS

- Repo: https://github.com/...
- AGENTS.md: Reglas de trabajo generales (incluye resumen de documentación)
- Este archivo: Referencia completa con ejemplos detallados
