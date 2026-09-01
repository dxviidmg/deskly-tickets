/**
 * Hook para suscribirse al stream de eventos de tickets via WebSocket.
 * 
 * Funcionalidades:
 * - Conexión automática al montar el componente
 * - Limpieza de la conexión al desmontar
 * - Reconexión automática con backoff exponencial
 * - Indica el estado de conexión (conectando, conectado, desconectado)
 * 
 * @example
 * ```tsx
 * const { status } = useTicketStream((event) => {
 *   if (event.tipo === "ticket.creado") {
 *     // Manejar nuevo ticket
 *   }
 * });
 * ```
 */
"use client";

import { useEffect, useRef, useState } from "react";
import type { TicketEvent } from "@/lib/types";

/** Estado de la conexión WebSocket */
export type ConnectionStatus = "conectando" | "conectado" | "desconectado";

/**
 * Devuelve la URL del WebSocket.
 * Usa la variable de entorno NEXT_PUBLIC_WS_URL o localhost por defecto.
 */
function wsUrl(): string {
  return (
    process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/ws/tickets"
  );
}

/**
 * Hook para suscribirse a eventos de tickets en tiempo real.
 * 
 * @param onEvent - Callback que se ejecuta cuando llega un evento
 * @returns Objeto con el estado de la conexión
 */
export function useTicketStream(onEvent: (event: TicketEvent) => void) {
  const [status, setStatus] = useState<ConnectionStatus>("conectando");

  // Mantener referencia al callback más reciente sin re-ejecutar el efecto
  const onEventRef = useRef(onEvent);
  useEffect(() => {
    onEventRef.current = onEvent;
  }, [onEvent]);

  useEffect(() => {
    let ws: WebSocket | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let closedByUs = false; // Para distinguir cierre intencional vs error
    let attempts = 0;

    /**
     * Establece la conexión WebSocket.
     * Se llama al montar y cuando se pierde la conexión.
     */
    const connect = () => {
      setStatus("conectando");
      ws = new WebSocket(wsUrl());

      // Conexión exitosa
      ws.onopen = () => {
        attempts = 0;
        setStatus("conectado");
      };

      // Mensaje recibido: parsear y pasar al callback
      ws.onmessage = (ev) => {
        try {
          const data = JSON.parse(ev.data) as TicketEvent;
          onEventRef.current(data);
        } catch {
          // Ignorar mensajes malformados
        }
      };

      // Conexión cerrada: reconectar si no fue intencional
      ws.onclose = () => {
        setStatus("desconectado");
        if (!closedByUs) {
          // Backoff exponencial con máximo de 5 segundos
          attempts += 1;
          const delay = Math.min(1000 * attempts, 5000);
          reconnectTimer = setTimeout(connect, delay);
        }
      };

      // Error: cerrar para que onclose maneje la reconexión
      ws.onerror = () => {
        ws?.close();
      };
    };

    // Iniciar conexión
    connect();

    // Limpieza al desmontar
    return () => {
      closedByUs = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      ws?.close();
    };
  }, []);

  return { status };
}
