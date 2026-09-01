/**
 * Dashboard principal - Lista de tickets.
 * 
 * Muestra una tabla paginada de tickets con:
 * - Filtros por estado, prioridad y asignado
 * - Actualizaciones en tiempo real via WebSocket
 * - Asignación de tickets directamente desde la tabla
 * - Indicador de estado de conexión
 * - Animación de highlight en filas actualizadas
 */
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

/** Tamaño de página para la paginación */
const PAGE_SIZE = 10;

/** Estados de carga de la página */
type LoadState = "loading" | "ready" | "error";

/** Labels en español para los estados */
const ESTADO_LABEL: Record<Estado, string> = {
  abierto: "Abierto",
  en_progreso: "En progreso",
  resuelto: "Resuelto",
  reabierto: "Reabierto",
  cerrado: "Cerrado",
};

/** Labels en español para las prioridades */
const PRIORIDAD_LABEL: Record<Prioridad, string> = {
  baja: "Baja",
  media: "Media",
  alta: "Alta",
  urgente: "Urgente",
};

/**
 * Página del dashboard protegida por autenticación.
 */
export default function DashboardPage() {
  return (
    <RequireAuth>
      <Dashboard />
    </RequireAuth>
  );
}

/**
 * Dashboard con la tabla de tickets y toda la lógica de estado.
 */
function Dashboard() {
  // Estado de datos y carga
  const [data, setData] = useState<Page<Ticket> | null>(null);
  const [state, setState] = useState<LoadState>("loading");
  const [error, setError] = useState<string>("");

  // Filtros activos
  const [estado, setEstado] = useState<Estado | "">("");
  const [prioridad, setPrioridad] = useState<Prioridad | "">("");
  const [asignadoAId, setAsignadoAId] = useState<number | null>(null);
  const [page, setPage] = useState(1);

  // Usuarios para el filtro de asignado
  const [users, setUsers] = useState<Array<{ id: number; email: string; nombre_completo: string }>>([]);

  // Cargar lista de usuarios para el filtro de asignado
  useEffect(() => {
    api
      .listUserOptions("", 50)
      .then(setUsers)
      .catch(() => setUsers([]));
  }, []);

  // Estado para asignación inline
  const [assigningId, setAssigningId] = useState<number | null>(null);
  const [assignError, setAssignError] = useState("");

  // IDs de filas con highlight (actualizadas recientemente)
  const [flashIds, setFlashIds] = useState<Set<number>>(new Set());

  /**
   * Añade highlight temporal a una fila.
   * El efecto dura 1.2 segundos.
   */
  const flashRow = useCallback((id: number) => {
    setFlashIds((prev) => new Set(prev).add(id));
    setTimeout(() => {
      setFlashIds((prev) => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
    }, 1200);
  }, []);

  /**
   * Cargar tickets desde la API.
   * Se ejecuta al cambiar filtros o página.
   */
  const load = useCallback(async () => {
    setState("loading");
    setError("");
    try {
      const res = await api.listTickets({
        page,
        size: PAGE_SIZE,
        estado,
        prioridad,
        asignado_a_id: asignadoAId,
      });
      setData(res);
      setState("ready");
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : "No se pudo cargar la lista";
      setError(msg);
      setState("error");
    }
  }, [page, estado, prioridad, asignadoAId]);

  useEffect(() => {
    load();
  }, [load]);

  /**
   * Asignar (o desasignar) un ticket desde la tabla.
   * Actualiza la fila in place sin recargar toda la lista.
   */
  const assignUser = useCallback(
    async (ticketId: number, userId: number | null) => {
      setAssigningId(ticketId);
      setAssignError("");
      try {
        const updated = await api.updateTicket(ticketId, {
          asignado_a_id: userId,
        });
        setData((prev) => {
          if (!prev) return prev;

          // Si el ticket ya no coincide con los filtros, quitarlo
          const stillMatches =
            (!estado || updated.estado === estado) &&
            (!prioridad || updated.prioridad === prioridad) &&
            (asignadoAId === null ||
              (asignadoAId === -1
                ? updated.asignado_a_id === null
                : updated.asignado_a_id === asignadoAId));

          if (!stillMatches) {
            return {
              ...prev,
              items: prev.items.filter((t) => t.id !== ticketId),
              total: Math.max(0, prev.total - 1),
            };
          }
          return {
            ...prev,
            items: prev.items.map((t) => (t.id === ticketId ? updated : t)),
          };
        });
        flashRow(ticketId);
      } catch (e) {
        setAssignError(
          e instanceof ApiError ? e.message : "No se pudo asignar el ticket"
        );
      } finally {
        setAssigningId(null);
      }
    },
    [estado, prioridad, asignadoAId, flashRow]
  );

  /**
   * Verificar si un ticket coincide con los filtros activos.
   */
  const matchesFilters = useCallback(
    (t: Ticket) => {
      if (estado && t.estado !== estado) return false;
      if (prioridad && t.prioridad !== prioridad) return false;
      if (asignadoAId !== null) {
        if (asignadoAId === -1) {
          if (t.asignado_a_id !== null) return false;
        } else if (t.asignado_a_id !== asignadoAId) {
          return false;
        }
      }
      return true;
    },
    [estado, prioridad, asignadoAId]
  );

  /**
   * Manejar eventos del WebSocket.
   * Actualiza la tabla in place sin mostrar skeleton.
   */
  const onEvent = useCallback(
    (event: TicketEvent) => {
      const incoming = event.datos;

      setData((prev) => {
        if (!prev) return prev;

        const idx = prev.items.findIndex((t) => t.id === incoming.id);
        const fits = matchesFilters(incoming);

        // Ticket existente que se actualizó
        if (idx !== -1) {
          // Si ya no coincide con filtros, quitarlo
          if (!fits) {
            const items = prev.items.filter((t) => t.id !== incoming.id);
            return { ...prev, items, total: Math.max(0, prev.total - 1) };
          }
          const items = [...prev.items];
          items[idx] = incoming;
          return { ...prev, items };
        }

        // Ticket nuevo que coincide con filtros
        if (fits && event.tipo === "ticket.creado") {
          const items =
            page === 1
              ? [incoming, ...prev.items].slice(0, PAGE_SIZE)
              : prev.items;
          return { ...prev, items, total: prev.total + 1 };
        }

        return prev;
      });

      // Highlight en tickets actualizados
      if (matchesFilters(incoming) && (page === 1 || event.tipo !== "ticket.creado")) {
        flashRow(incoming.id);
      }
    },
    [matchesFilters, page, flashRow]
  );

  const { status } = useTicketStream(onEvent);

  const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

  return (
    <div>
      {/* Cabecera con título e indicador de conexión */}
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-lg font-semibold">Tickets</h1>
        <ConnectionIndicator status={status} />
      </div>

      {/* Filtros */}
      <div className="mb-4 grid grid-cols-3 gap-4">
        {/* Filtro por estado */}
        <div className="flex flex-col gap-2">
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
            className="w-full rounded-md border border-slate-300 bg-white px-2 py-1 text-sm"
          >
            <option value="">Todos</option>
            {ESTADOS.map((e) => (
              <option key={e} value={e}>
                {ESTADO_LABEL[e]}
              </option>
            ))}
          </select>
        </div>

        {/* Filtro por prioridad */}
        <div className="flex flex-col gap-2">
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
            className="w-full rounded-md border border-slate-300 bg-white px-2 py-1 text-sm"
          >
            <option value="">Todas</option>
            {PRIORIDADES.map((p) => (
              <option key={p} value={p}>
                {PRIORIDAD_LABEL[p]}
              </option>
            ))}
          </select>
        </div>

        {/* Filtro por asignado */}
        <div className="flex flex-col gap-2">
          <label htmlFor="asignado" className="text-sm text-slate-600">
            Filtrar por asignado:
          </label>
          <select
            id="asignado"
            value={asignadoAId === null ? "" : asignadoAId === -1 ? "-1" : asignadoAId}
            onChange={(e) => {
              setPage(1);
              if (e.target.value === "") {
                setAsignadoAId(null);
              } else if (e.target.value === "-1") {
                setAsignadoAId(-1);
              } else {
                setAsignadoAId(Number(e.target.value));
              }
            }}
            className="w-full rounded-md border border-slate-300 bg-white px-2 py-1 text-sm"
          >
            <option value="">Todos</option>
            <option value="-1">Sin asignar</option>
            {users.map((u) => (
              <option key={u.id} value={u.id}>
                {u.nombre_completo} ({u.email})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Estados de carga */}
      {state === "loading" && <TableSkeleton />}
      {state === "error" && <ErrorState mensaje={error} onReintentar={load} />}
      {state === "ready" && data && data.items.length === 0 && (
        <EmptyState mensaje="Sin tickets" />
      )}

      {/* Tabla de tickets */}
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
                  <tr
                    key={t.id}
                    className={`border-t hover:bg-slate-50 ${
                      flashIds.has(t.id) ? "ticket-row-flash" : ""
                    }`}
                  >
                    {/* Título con enlace al detalle */}
                    <td className="px-4 py-2">
                      <Link
                        href={`/tickets/${t.id}`}
                        className="font-medium text-blue-700 hover:underline"
                      >
                        {t.titulo}
                      </Link>
                    </td>
                    {/* Badge de estado */}
                    <td className="px-4 py-2">
                      <EstadoBadge estado={t.estado} />
                    </td>
                    {/* Badge de prioridad */}
                    <td className="px-4 py-2">
                      <PrioridadBadge prioridad={t.prioridad} />
                    </td>
                    {/* Selector de asignado */}
                    <td className="px-4 py-2">
                      <UserAutocomplete
                        currentEmail={t.asignado_a}
                        onSelect={(userId) => assignUser(t.id, userId)}
                        disabled={assigningId === t.id}
                        className="w-56"
                      />
                    </td>
                    {/* Fecha relativa */}
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

          {/* Paginación */}
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
