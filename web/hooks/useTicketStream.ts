"use client";

import { useEffect, useRef, useState } from "react";
import type { TicketEvent } from "@/lib/types";

export type ConnectionStatus = "conectando" | "conectado" | "desconectado";

function wsUrl(): string {
  return (
    process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/ws/tickets"
  );
}

/**
 * Subscribe to the backend WebSocket stream of ticket events.
 *
 * - Cleans up the socket on unmount (useEffect cleanup).
 * - Exposes the connection status for a visible indicator.
 * - Reconnects automatically with a small backoff when the connection drops
 *   (bonus).
 */
export function useTicketStream(onEvent: (event: TicketEvent) => void) {
  const [status, setStatus] = useState<ConnectionStatus>("conectando");

  // Keep the latest callback without forcing the effect to re-run.
  const onEventRef = useRef(onEvent);
  useEffect(() => {
    onEventRef.current = onEvent;
  }, [onEvent]);

  useEffect(() => {
    let ws: WebSocket | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let closedByUs = false;
    let attempts = 0;

    const connect = () => {
      setStatus("conectando");
      ws = new WebSocket(wsUrl());

      ws.onopen = () => {
        attempts = 0;
        setStatus("conectado");
      };

      ws.onmessage = (ev) => {
        try {
          const data = JSON.parse(ev.data) as TicketEvent;
          onEventRef.current(data);
        } catch {
          // Ignore malformed messages.
        }
      };

      ws.onclose = () => {
        setStatus("desconectado");
        if (!closedByUs) {
          // Exponential-ish backoff capped at 5s.
          attempts += 1;
          const delay = Math.min(1000 * attempts, 5000);
          reconnectTimer = setTimeout(connect, delay);
        }
      };

      ws.onerror = () => {
        // Let onclose drive the reconnect logic.
        ws?.close();
      };
    };

    connect();

    return () => {
      closedByUs = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      ws?.close();
    };
  }, []);

  return { status };
}
