/**
 * Componente cliente para el detalle de ticket.
 * 
 * Funcionalidades:
 * - Edición inline de título y descripción (estilo Jira)
 * - Transiciones de estado con comentario opcional
 * - Asignación de usuario
 * - Comentarios en hilo
 * - Historial de cambios (state_log)
 * - Actualizaciones en tiempo real via WebSocket
 */
"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";
import type { Estado, TicketDetail, TicketEvent } from "@/lib/types";
import { TRANSICIONES_VALIDAS } from "@/lib/types";
import { EstadoBadge, PrioridadBadge } from "@/components/Badges";
import { ConnectionIndicator } from "@/components/ConnectionIndicator";
import { UserAutocomplete } from "@/components/UserAutocomplete";
import { useTicketStream } from "@/hooks/useTicketStream";
import { tiempoRelativo } from "@/lib/time";

/** Labels en español para los estados */
const ESTADO_LABEL: Record<Estado, string> = {
  abierto: "Abierto",
  en_progreso: "En progreso",
  resuelto: "Resuelto",
  reabierto: "Reabierto",
  cerrado: "Cerrado",
};

/**
 * Componente interactivo para el detalle de un ticket.
 * 
 * @param initial - Datos iniciales del ticket (cargados en SSR)
 */
export function TicketDetailClient({ initial }: { initial: TicketDetail }) {
  // Estado del ticket
  const [ticket, setTicket] = useState<TicketDetail>(initial);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  // Campos editables (edición inline estilo Jira)
  const [titulo, setTitulo] = useState(initial.titulo);
  const [descripcion, setDescripcion] = useState(initial.descripcion);

  // Formulario de comentario
  const [cuerpo, setCuerpo] = useState("");

  // Modal de transición (pide nota opcional explicando el cambio)
  const [transitionTarget, setTransitionTarget] = useState<Estado | null>(null);
  const [transitionComment, setTransitionComment] = useState("");

  // Modal de historial (audit trail del ticket)
  const [showHistory, setShowHistory] = useState(false);

  // Sincronizar campos editables cuando el ticket se actualiza
  // (por ejemplo, via WebSocket), salvo que haya cambios pendientes
  useEffect(() => {
    setTitulo(ticket.titulo);
    setDescripcion(ticket.descripcion);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ticket.titulo, ticket.descripcion]);

  /** Verificar si hay cambios pendientes de guardar */
  const dirty =
    titulo.trim() !== ticket.titulo || descripcion.trim() !== ticket.descripcion;

  /**
   * Recargar el ticket desde la API.
   * Se usa tras actualizaciones para sincronizar estado.
   */
  const refresh = useCallback(async () => {
    try {
      const fresh = await api.getTicket(initial.id);
      setTicket(fresh);
    } catch {
      // Mantener estado actual si falla la recarga
    }
  }, [initial.id]);

  /**
   * Guardar cambios en título y descripción.
   */
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

  /**
   * Manejar eventos del WebSocket.
   * Solo recarga si el evento es para este ticket.
   */
  const onEvent = useCallback(
    (event: TicketEvent) => {
      if (event.datos.id === initial.id) refresh();
    },
    [initial.id, refresh]
  );
  const { status } = useTicketStream(onEvent);

  /**
   * Iniciar transición de estado.
   * Abre el modal para capturar nota opcional.
   */
  const doTransition = (nuevo: Estado) => {
    setError("");
    setTransitionTarget(nuevo);
    setTransitionComment("");
  };

  /**
   * Confirmar transición de estado.
   * Ejecuta la transición y añade comentario opcional.
   */
  const confirmTransition = async () => {
    if (transitionTarget === null) return;
    const nuevo = transitionTarget;
    setBusy(true);
    setError("");
    try {
      await api.transition(ticket.id, nuevo);
      // Nota opcional explicando el cambio (estilo Jira)
      const nota = transitionComment.trim();
      if (nota) {
        await api.addComment(
          ticket.id,
          `Estado: ${ESTADO_LABEL[ticket.estado]} → ${ESTADO_LABEL[nuevo]}\n${nota}`
        );
      }
      setTransitionTarget(null);
      setTransitionComment("");
      await refresh();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No se pudo cambiar el estado");
    } finally {
      setBusy(false);
    }
  };

  /**
   * Enviar un nuevo comentario.
   */
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

  /**
   * Asignar (o desasignar) el ticket a un usuario.
   */
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

  // Transiciones válidas desde el estado actual
  const posibles = TRANSICIONES_VALIDAS[ticket.estado] || [];

  return (
    <div className="mt-4 space-y-4">
      {/* Cabecera con navegación y acciones */}
      <div className="flex items-center justify-between">
        <Link href="/" className="text-sm text-blue-700 hover:underline">
          ← Volver al listado
        </Link>
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => setShowHistory(true)}
            className="rounded-md border border-slate-300 px-3 py-1 text-sm text-slate-600 hover:bg-slate-50"
          >
            Historial ({ticket.state_log.length})
          </button>
          <ConnectionIndicator status={status} />
        </div>
      </div>

      {/* Estado, prioridad, transición y asignación */}
      <div className="rounded-lg border bg-white p-4">
        <div className={`grid gap-4 ${posibles.length === 0 ? "sm:grid-cols-3" : "sm:grid-cols-2 lg:grid-cols-4"}`}>
          {/* Estado actual */}
          <div>
            <h2 className="mb-2 text-sm font-medium text-slate-700">Estado</h2>
            <EstadoBadge estado={ticket.estado} />
          </div>

          {/* Prioridad */}
          <div>
            <h2 className="mb-2 text-sm font-medium text-slate-700">
              Prioridad
            </h2>
            <PrioridadBadge prioridad={ticket.prioridad} />
          </div>

          {/* Transiciones o info de resolución */}
          <div className="lg:border-l lg:border-slate-100 lg:pl-4">
            <h2 className="mb-2 text-sm font-medium text-slate-700">
              {posibles.length === 0 ? "Resuelto por" : "Cambiar estado"}
            </h2>
            {posibles.length === 0 ? (
              <p className="text-sm text-slate-500">
                {ticket.asignado_a || "sin asignar"}
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

          {/* Asignación (solo si hay transiciones disponibles) */}
          {posibles.length > 0 && (
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
          )}
        </div>
      </div>

      {/* Mensaje de error */}
      {error && (
        <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      )}

      {/* Título y descripción editables (estilo Jira) */}
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

        {/* Botones de guardar/cancelar */}
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

      {/* Comentarios */}
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

        {/* Formulario de nuevo comentario */}
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

      {/* Modal de transición: pedir nota opcional */}
      {transitionTarget !== null && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
          onClick={() => !busy && setTransitionTarget(null)}
        >
          <div
            className="w-full max-w-md rounded-lg bg-white p-5 shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="text-base font-semibold text-slate-800">
              Cambiar estado
            </h2>
            <p className="mt-1 flex items-center gap-2 text-sm text-slate-600">
              <EstadoBadge estado={ticket.estado} />
              <span aria-hidden>→</span>
              <EstadoBadge estado={transitionTarget} />
            </p>

            <label className="mt-4 block text-sm text-slate-600">
              Comentario (opcional): explica por qué cambia el estado
            </label>
            <textarea
              autoFocus
              value={transitionComment}
              onChange={(e) => setTransitionComment(e.target.value)}
              disabled={busy}
              rows={3}
              placeholder="Ej.: Se resolvió tras reiniciar el servicio."
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm disabled:opacity-50"
            />

            <div className="mt-4 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setTransitionTarget(null)}
                disabled={busy}
                className="rounded-md border border-slate-300 px-4 py-1.5 text-sm text-slate-600 hover:bg-slate-50 disabled:opacity-50"
              >
                Cancelar
              </button>
              <button
                type="button"
                onClick={confirmTransition}
                disabled={busy}
                className="rounded-md bg-blue-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {busy ? "Cambiando…" : "Confirmar cambio"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal de historial: audit trail del ticket */}
      {showHistory && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
          onClick={() => setShowHistory(false)}
        >
          <div
            className="flex max-h-[80vh] w-full max-w-md flex-col rounded-lg bg-white shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between border-b px-5 py-3">
              <h2 className="text-base font-semibold text-slate-800">
                Historial de cambios
              </h2>
              <button
                type="button"
                onClick={() => setShowHistory(false)}
                aria-label="Cerrar"
                className="rounded-md p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
              >
                ✕
              </button>
            </div>

            <div className="overflow-y-auto px-5 py-4">
              {ticket.state_log.length === 0 ? (
                <p className="text-sm text-slate-500">
                  Aún no hay cambios registrados.
                </p>
              ) : (
                <ol className="space-y-3">
                  {ticket.state_log.map((log) => (
                    <li
                      key={log.id}
                      className="border-l-2 border-slate-200 pl-3"
                    >
                      <p className="text-sm text-slate-700">{log.mensaje}</p>
                      <div className="mt-1 text-xs text-slate-400">
                        <span>{new Date(log.creado_en).toLocaleString()}</span>
                        <span className="ml-2 text-slate-300">·</span>
                        <span className="ml-2">{tiempoRelativo(log.creado_en)}</span>
                      </div>
                    </li>
                  ))}
                </ol>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
