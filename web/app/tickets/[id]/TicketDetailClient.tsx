"use client";

import { useCallback, useState } from "react";
import { api, ApiError } from "@/lib/api";
import type { Estado, TicketDetail, TicketEvent } from "@/lib/types";
import { TRANSICIONES_VALIDAS } from "@/lib/types";
import { EstadoBadge } from "@/components/Badges";
import { ConnectionIndicator } from "@/components/ConnectionIndicator";
import { useTicketStream } from "@/hooks/useTicketStream";

const ESTADO_LABEL: Record<Estado, string> = {
  abierto: "Abierto",
  en_progreso: "En progreso",
  resuelto: "Resuelto",
  cerrado: "Cerrado",
};

export function TicketDetailClient({ initial }: { initial: TicketDetail }) {
  const [ticket, setTicket] = useState<TicketDetail>(initial);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  // Comment form
  const [cuerpo, setCuerpo] = useState("");

  const refresh = useCallback(async () => {
    try {
      const fresh = await api.getTicket(initial.id);
      setTicket(fresh);
    } catch {
      // keep current state on refresh error
    }
  }, [initial.id]);

  // Live updates: react only to events for this ticket.
  const onEvent = useCallback(
    (event: TicketEvent) => {
      if (event.datos.id === initial.id) refresh();
    },
    [initial.id, refresh]
  );
  const { status } = useTicketStream(onEvent);

  const doTransition = async (nuevo: Estado) => {
    setBusy(true);
    setError("");
    try {
      await api.transition(ticket.id, nuevo);
      await refresh();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No se pudo cambiar el estado");
    } finally {
      setBusy(false);
    }
  };

  const submitComment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!cuerpo.trim()) return;
    setBusy(true);
    setError("");
    try {
      await api.addComment(ticket.id, cuerpo.trim());
      setCuerpo("");
      await refresh();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No se pudo comentar");
    } finally {
      setBusy(false);
    }
  };

  const posibles = TRANSICIONES_VALIDAS[ticket.estado];

  return (
    <div className="mt-4 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm text-slate-600">
          Estado actual: <EstadoBadge estado={ticket.estado} />
        </div>
        <ConnectionIndicator status={status} />
      </div>

      {/* Transition buttons */}
      <div className="rounded-lg border bg-white p-4">
        <h2 className="mb-2 text-sm font-medium text-slate-700">
          Cambiar estado
        </h2>
        {posibles.length === 0 ? (
          <p className="text-sm text-slate-500">
            No hay transiciones disponibles desde este estado.
          </p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {posibles.map((nuevo) => (
              <button
                key={nuevo}
                disabled={busy}
                onClick={() => doTransition(nuevo)}
                className="rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {ESTADO_LABEL[nuevo]}
              </button>
            ))}
          </div>
        )}
      </div>

      {error && (
        <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      )}

      {/* Comments */}
      <div className="rounded-lg border bg-white p-4">
        <h2 className="mb-3 text-sm font-medium text-slate-700">
          Comentarios ({ticket.comments.length})
        </h2>

        {ticket.comments.length === 0 ? (
          <p className="text-sm text-slate-500">Aún no hay comentarios.</p>
        ) : (
          <ul className="space-y-3">
            {ticket.comments.map((c) => (
              <li key={c.id} className="rounded-md bg-slate-50 p-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">{c.autor}</span>
                  <span className="text-xs text-slate-400">
                    {new Date(c.creado_en).toLocaleString()}
                  </span>
                </div>
                <p className="mt-1 whitespace-pre-wrap text-sm text-slate-700">
                  {c.cuerpo}
                </p>
              </li>
            ))}
          </ul>
        )}

        <form onSubmit={submitComment} className="mt-4 space-y-2">
          <textarea
            value={cuerpo}
            onChange={(e) => setCuerpo(e.target.value)}
            placeholder="Escribe un comentario…"
            rows={3}
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
          <button
            type="submit"
            disabled={busy || !cuerpo.trim()}
            className="rounded-md bg-slate-800 px-4 py-2 text-sm font-medium text-white hover:bg-slate-900 disabled:opacity-50"
          >
            Comentar
          </button>
        </form>
      </div>
    </div>
  );
}
