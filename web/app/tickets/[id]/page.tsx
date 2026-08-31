import Link from "next/link";
import { notFound } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { EstadoBadge, PrioridadBadge } from "@/components/Badges";
import { TicketDetailClient } from "./TicketDetailClient";

// Server Component: fetches the ticket on the server (SSR) so the first paint
// already contains the ticket and its comments.
export default async function TicketDetailPage({
  params,
}: {
  params: { id: string };
}) {
  const id = Number(params.id);
  if (!Number.isInteger(id) || id <= 0) notFound();

  try {
    const ticket = await api.getTicket(id);
    return (
      <div>
        <Link href="/" className="text-sm text-blue-700 hover:underline">
          ← Volver al listado
        </Link>

        <div className="mt-3 rounded-lg border bg-white p-5">
          <div className="flex items-start justify-between">
            <h1 className="text-xl font-semibold">{ticket.titulo}</h1>
            <div className="flex gap-2">
              <EstadoBadge estado={ticket.estado} />
              <PrioridadBadge prioridad={ticket.prioridad} />
            </div>
          </div>
          <p className="mt-3 whitespace-pre-wrap text-slate-700">
            {ticket.descripcion}
          </p>
          <p className="mt-3 text-sm text-slate-500">
            Asignado a: {ticket.asignado_a ?? "—"}
          </p>
        </div>

        {/* Interactivity (transitions, comments, live updates) on the client. */}
        <TicketDetailClient initial={ticket} />
      </div>
    );
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) notFound();
    throw e;
  }
}
