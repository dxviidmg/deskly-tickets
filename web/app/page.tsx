"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";
import type { Estado, Page, Prioridad, Ticket, TicketEvent } from "@/lib/types";
import { ESTADOS, PRIORIDADES } from "@/lib/types";
import { tiempoRelativo } from "@/lib/time";
import { EstadoBadge, PrioridadBadge } from "@/components/Badges";
import { TableSkeleton, EmptyState, ErrorState } from "@/components/UiStates";
import { ConnectionIndicator } from "@/components/ConnectionIndicator";
import { UserAutocomplete } from "@/components/UserAutocomplete";
import { useTicketStream } from "@/hooks/useTicketStream";
import { RequireAuth } from "@/components/RequireAuth";

const PAGE_SIZE = 10;

type LoadState = "loading" | "ready" | "error";

const ESTADO_LABEL: Record<Estado, string> = {
  abierto: "Abierto",
  en_progreso: "En progreso",
  resuelto: "Resuelto",
  cerrado: "Cerrado",
};

const PRIORIDAD_LABEL: Record<Prioridad, string> = {
  baja: "Baja",
  media: "Media",
  alta: "Alta",
  urgente: "Urgente",
};

export default function DashboardPage() {
  return (
    <RequireAuth>
      <Dashboard />
    </RequireAuth>
  );
}

function Dashboard() {
  const [data, setData] = useState<Page<Ticket> | null>(null);
  const [state, setState] = useState<LoadState>("loading");
  const [error, setError] = useState<string>("");
  const [estado, setEstado] = useState<Estado | "">("");
  const [prioridad, setPrioridad] = useState<Prioridad | "">("");
  const [page, setPage] = useState(1);
  // Inline assignment (from the table) state.
  const [assigningId, setAssigningId] = useState<number | null>(null);
  const [assignError, setAssignError] = useState("");

  const load = useCallback(async () => {
    setState("loading");
    setError("");
    try {
      const res = await api.listTickets({ page, size: PAGE_SIZE, estado, prioridad });
      setData(res);
      setState("ready");
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : "No se pudo cargar la lista";
      setError(msg);
      setState("error");
    }
  }, [page, estado, prioridad]);

  useEffect(() => {
    load();
  }, [load]);

  // Assign (or clear) a ticket's assignee directly from the table row, reusing
  // the same endpoint as the detail view. Refreshes the list afterwards.
  const assignUser = useCallback(
    async (ticketId: number, userId: number | null) => {
      setAssigningId(ticketId);
      setAssignError("");
      try {
        await api.updateTicket(ticketId, { asignado_a_id: userId });
        await load();
      } catch (e) {
        setAssignError(
          e instanceof ApiError ? e.message : "No se pudo asignar el ticket"
        );
      } finally {
        setAssigningId(null);
      }
    },
    [load]
  );

  // Live updates: refresh the current view when a ticket event arrives.
  const onEvent = useCallback(
    (_event: TicketEvent) => {
      load();
    },
    [load]
  );
  const { status } = useTicketStream(onEvent);

  const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-lg font-semibold">Tickets</h1>
        <ConnectionIndicator status={status} />
      </div>

      <div className="mb-4 flex flex-wrap items-center gap-4">
        <div className="flex items-center gap-2">
          <label htmlFor="estado" className="text-sm text-slate-600">
            Filtrar por estado:
          </label>
          <select
            id="estado"
            value={estado}
            onChange={(e) => {
              setPage(1);
              setEstado(e.target.value as Estado | "");
            }}
            className="rounded-md border border-slate-300 bg-white px-2 py-1 text-sm"
          >
            <option value="">Todos</option>
            {ESTADOS.map((e) => (
              <option key={e} value={e}>
                {ESTADO_LABEL[e]}
              </option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-2">
          <label htmlFor="prioridad" className="text-sm text-slate-600">
            Filtrar por prioridad:
          </label>
          <select
            id="prioridad"
            value={prioridad}
            onChange={(e) => {
              setPage(1);
              setPrioridad(e.target.value as Prioridad | "");
            }}
            className="rounded-md border border-slate-300 bg-white px-2 py-1 text-sm"
          >
            <option value="">Todas</option>
            {PRIORIDADES.map((p) => (
              <option key={p} value={p}>
                {PRIORIDAD_LABEL[p]}
              </option>
            ))}
          </select>
        </div>
      </div>

      {state === "loading" && <TableSkeleton />}

      {state === "error" && (
        <ErrorState mensaje={error} onReintentar={load} />
      )}

      {state === "ready" && data && data.items.length === 0 && (
        <EmptyState mensaje="Sin tickets" />
      )}

      {state === "ready" && data && data.items.length > 0 && (
        <>
          {assignError && (
            <p className="mb-3 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
              {assignError}
            </p>
          )}
          <div className="rounded-lg border bg-white">
            <table className="w-full text-sm">
              <thead className="bg-slate-100 text-left text-slate-600">
                <tr>
                  <th className="px-4 py-2 font-medium">Título</th>
                  <th className="px-4 py-2 font-medium">Estado</th>
                  <th className="px-4 py-2 font-medium">Prioridad</th>
                  <th className="px-4 py-2 font-medium">Asignado</th>
                  <th className="px-4 py-2 font-medium">Creado</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((t) => (
                  <tr key={t.id} className="border-t hover:bg-slate-50">
                    <td className="px-4 py-2">
                      <Link
                        href={`/tickets/${t.id}`}
                        className="font-medium text-blue-700 hover:underline"
                      >
                        {t.titulo}
                      </Link>
                    </td>
                    <td className="px-4 py-2">
                      <EstadoBadge estado={t.estado} />
                    </td>
                    <td className="px-4 py-2">
                      <PrioridadBadge prioridad={t.prioridad} />
                    </td>
                    <td className="px-4 py-2">
                      <UserAutocomplete
                        currentEmail={t.asignado_a}
                        onSelect={(userId) => assignUser(t.id, userId)}
                        disabled={assigningId === t.id}
                        className="w-56"
                      />
                    </td>
                    <td
                      className="px-4 py-2 text-slate-500"
                      title={new Date(t.creado_en).toLocaleString()}
                    >
                      {tiempoRelativo(t.creado_en)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="mt-4 flex items-center justify-between text-sm">
            <span className="text-slate-500">
              {data.total} ticket(s) · página {data.page} de {totalPages}
            </span>
            <div className="flex gap-2">
              <button
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                className="rounded-md border border-slate-300 bg-white px-3 py-1 disabled:opacity-40"
              >
                Anterior
              </button>
              <button
                disabled={page >= totalPages}
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                className="rounded-md border border-slate-300 bg-white px-3 py-1 disabled:opacity-40"
              >
                Siguiente
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
