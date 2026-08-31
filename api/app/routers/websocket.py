"""WebSocket endpoint for real-time ticket events."""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.ws import manager

router = APIRouter()


@router.websocket("/ws/tickets")
async def ticket_stream(websocket: WebSocket) -> None:
    await manager.connect(websocket)
    try:
        while True:
            # We don't expect client messages; receiving keeps the socket open
            # and lets us detect disconnects promptly.
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception:
        # Any other error also results in a clean removal from the registry.
        await manager.disconnect(websocket)
