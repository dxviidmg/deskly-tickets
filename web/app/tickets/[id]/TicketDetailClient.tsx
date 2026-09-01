"use client";

import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import type { Estado, TicketDetail, TicketEvent } from "@/lib/types";
import { TRANSICIONES_VALIDAS } from "@/lib/types";
import { EstadoBadge, PrioridadBadge } from "@/components/Badges";
import { ConnectionIndicator } from "@/components/ConnectionIndicator";
import { UserAutocomplete } from "@/components/UserAutocomplete";
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

  // Inline edit (Jira-style) for title and description.
  const [titulo, setTitulo] = useState(initial.titulo);
  const [descripcion, setDescripcion] = useState(initial.descripcion);

  // Comment form
  const [cuerpo, setCuerpo] = useState("");

  // Keep the editable fields in sync when the ticket is refreshed (e.g. via
  // WebSocket) — unless the user has unsaved local edits.
  useEffect(() => {
    setTitulo(ticket.titulo);
    setDescripcion(ticket.descripcion);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ticket.titulo, ticket.descripcion]);

  const dirty =
    titulo.trim() !== ticket.titulo || descripcion.trim() !== ticket.descripcion;

  const refresh = useCallback(async () => {
    try {
      const fresh = await api.getTicket(initial.id);
      setTicket(fresh);
    } catch {
      // keep current state on refresh error
    }
  }, [initial.id]);

  const saveDetails = async () => {
    if (!titulo.trim() || !descripcion.trim()) {
      setError("El título y la descripción no pueden estar vacíos");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await api.updateTicket(ticket.id, {
        titulo: titulo.trim(),
        descripcion: descripcion.trim(),
      });
      await refresh();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No se pudo guardar el ticket");
    } finally {
      setBusy(false);
    }
  };

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

  const assignUser = async (userId: number | null) => {
    setBusy(true);
    setError("");
    try {
      await api.updateTicket(ticket.id, { asignado_a_id: userId });
      await refresh();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No se pudo asignar");
    } finally {
      setBusy(false);
    }
  };

  const posibles = TRANSICIONES_VALIDAS[ticket.estado];

  return (
    <div className="mt-4 space-y-4">
      <div className="flex items-center justify-end">
        <ConnectionIndicator status={status} />
      </div>

      {/* Estado, prioridad, transición y asignación en una fila (columnas). */}
      <div className="rounded-lg border bg-white p-4">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div>
            <h2 className="mb-2 text-sm font-medium text-slate-700">Estado</h2>
            <EstadoBadge estado={ticket.estado} />
          </div>

          <div>
            <h2 className="mb-2 text-sm font-medium text-slate-700">
              Prioridad
            </h2>
            <PrioridadBadge prioridad={ticket.prioridad} />
          </div>

          <div className="lg:border-l lg:border-slate-100 lg:pl-4">
            <h2 className="mb-2 text-sm font-medium text-slate-700">
              Cambiar estado
            </h2>
            {posibles.length === 0 ? (
              <p className="text-sm text-slate-500">
                No hay transiciones disponibles.
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

          <div className="lg:border-l lg:border-slate-100 lg:pl-4">
            <h2 className="mb-2 text-sm font-medium text-slate-700">
              Asignado a
            </h2>
            <UserAutocomplete
              currentEmail={ticket.asignado_a}
              onSelect={assignUser}
              disabled={busy}
              className="w-full"
            />
          </div>
        </div>
      </div>

      {error && (
        <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      )}

      {/* Título y descripción editables (estilo Jira). */}
      <div className="rounded-lg border bg-white p-5">
        <input
          value={titulo}
          onChange={(e) => setTitulo(e.target.value)}
          disabled={busy}
          maxLength={200}
          placeholder="Título del ticket"
          className="w-full rounded-md border border-transparent px-2 py-1 text-xl font-semibold hover:border-slate-200 focus:border-slate-300 focus:outline-none disabled:opacity-50"
        />

        <textarea
          value={descripcion}
          onChange={(e) => setDescripcion(e.target.value)}
          disabled={busy}
          rows={4}
          placeholder="Descripción del ticket"
          className="mt-3 w-full resize-y rounded-md border border-transparent px-2 py-1 text-slate-700 hover:border-slate-200 focus:border-slate-300 focus:outline-none disabled:opacity-50"
        />

        <div className="mt-3 flex items-center gap-2">
          <button
            type="button"
            onClick={saveDetails}
            disabled={busy || !dirty}
            className="rounded-md bg-blue-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Guardar cambios
          </button>
          {dirty && (
            <button
              type="button"
              onClick={() => {
                setTitulo(ticket.titulo);
                setDescripcion(ticket.descripcion);
                setError("");
              }}
              disabled={busy}
              className="rounded-md border border-slate-300 px-4 py-1.5 text-sm text-slate-600 hover:bg-slate-50 disabled:opacity-50"
            >
              Cancelar
            </button>
          )}
        </div>
      </div>

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
