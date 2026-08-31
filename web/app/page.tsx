"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";
import type { Estado, Page, Ticket, TicketEvent } from "@/lib/types";
import { ESTADOS } from "@/lib/types";
import { EstadoBadge, PrioridadBadge } from "@/components/Badges";
import { TableSkeleton, EmptyState, ErrorState } from "@/components/UiStates";
import { ConnectionIndicator } from "@/components/ConnectionIndicator";
import { useTicketStream } from "@/hooks/useTicketStream";

const PAGE_SIZE = 10;

type LoadState = "loading" | "ready" | "error";

const ESTADO_LABEL: Record<Estado, string> = {
  abierto: "Abierto",
  en_progreso: "En progreso",
  resuelto: "Resuelto",
  cerrado: "Cerrado",
};

export default function DashboardPage() {
  const [data, setData] = useState<Page<Ticket> | null>(null);
  const [state, setState] = useState<LoadState>("loading");
  const [error, setError] = useState<string>("");
  const [estado, setEstado] = useState<Estado | "">("");
  const [page, setPage] = useState(1);

  const load = useCallback(async () => {
    setState("loading");
    setError("");
    try {
      const res = await api.listTickets({ page, size: PAGE_SIZE, estado });
      setData(res);
      setState("ready");
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : "No se pudo cargar la lista";
      setError(msg);
      setState("error");
    }
  }, [page, estado]);

  useEffect(() => {
    load();
  }, [load]);

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

      <div className="mb-4 flex items-center gap-2">
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

      {state === "loading" && <TableSkeleton />}

      {state === "error" && (
        <ErrorState mensaje={error} onReintentar={load} />
      )}

      {state === "ready" && data && data.items.length === 0 && (
        <EmptyState mensaje="Sin tickets" />
      )}

      {state === "ready" && data && data.items.length > 0 && (
        <>
          <div className="overflow-hidden rounded-lg border bg-white">
            <table className="w-full text-sm">
              <thead className="bg-slate-100 text-left text-slate-600">
                <tr>
                  <th className="px-4 py-2 font-medium">Título</th>
                  <th className="px-4 py-2 font-medium">Estado</th>
                  <th className="px-4 py-2 font-medium">Prioridad</th>
                  <th className="px-4 py-2 font-medium">Asignado</th>
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
                    <td className="px-4 py-2 text-slate-600">
                      {t.asignado_a ?? "—"}
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
