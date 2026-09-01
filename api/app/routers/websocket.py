"""
MÓDULO: routers/websocket.py - Endpoint WebSocket para eventos en tiempo real

Endpoint para que los clientes se conecten y reciban eventos en tiempo real.

¿Cómo funciona?
1. Cliente conecta a ws://localhost:8000/ws/tickets
2. Servidor acepta y guarda la conexión en memory
3. Cada vez que ocurre un evento (ticket creado, actualizado, etc.):
   - El router publica el evento vía manager.broadcast()
   - manager lo distribuye a través de Redis (múltiples instancias)
   - Cada instancia envía el evento a sus clientes WebSocket
4. Cliente recibe eventos en tiempo real
5. Cuando se desconecta (cierre, error, timeout), se elimina la conexión

Mensaje WebSocket:
    {
        "tipo": "ticket.creado",
        "datos": {
            "id": 123,
            "titulo": "...",
            "estado": "abierto",
            ...
        }
    }

El frontend se mantiene actualizado sin necesidad de polling (no hace requests
cada 5 segundos, sino que recibe push notifications en tiempo real).
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.ws import manager

router = APIRouter()


@router.websocket("/ws/tickets")
async def ticket_stream(websocket: WebSocket) -> None:
    """
    WebSocket endpoint para recibir eventos de tickets en tiempo real.
    
    Proceso:
    1. Aceptar la conexión y agregar a _connections
    2. Esperar indefinidamente por mensajes del cliente
    3. Cuando se desconecta (el cliente cierra, error, timeout):
       - Capturar WebSocketDisconnect
       - Eliminar la conexión de _connections
    4. Para cualquier otro error: también eliminar la conexión
    
    Nota: El servidor NO espera mensajes del cliente (no hace nada con ellos).
    Solo mantiene la conexión abierta para poder enviar eventos.
    receive_text() es un "heartbeat": detecta si el cliente sigue conectado.
    
    Args:
        websocket (WebSocket): Conexión WebSocket del cliente
        
    Flujo:
    
    Cliente → Conecta a /ws/tickets
    Servidor → manager.connect(websocket)
    
    Loop infinito:
        receive_text()  [espera sin hacer nada]
        
    Cliente se desconecta o falla:
        WebSocketDisconnect / Exception
        manager.disconnect(websocket)
        
    Ejemplo de uso desde JavaScript:
        const ws = new WebSocket('ws://localhost:8000/ws/tickets');
        ws.onmessage = (event) => {
            const msg = JSON.parse(event.data);
            console.log('Evento:', msg.tipo, msg.datos);
            // Actualizar UI (agregar row a tabla, cambiar color, etc.)
        };
        ws.onerror = () => console.error('Error en WebSocket');
        ws.onclose = () => console.log('Desconectado');
    """
    # Aceptar conexión WebSocket y agregar al conjunto de conexiones
    await manager.connect(websocket)
    
    try:
        # Loop infinito: esperar mensajes (no haremos nada con ellos)
        # receive_text() bloquea hasta que el cliente envíe algo O se desconecte
        while True:
            # Esperar a que el cliente envíe un mensaje
            # En la práctica, no esperamos que envíe nada; esto solo
            # es para detectar cuando se desconecta
            await websocket.receive_text()
    except WebSocketDisconnect:
        # Cliente cerró la conexión normalmente
        await manager.disconnect(websocket)
    except Exception:
        # Cualquier otro error (timeout, conexión perdida, etc.)
        # También eliminamos la conexión
        await manager.disconnect(websocket)
