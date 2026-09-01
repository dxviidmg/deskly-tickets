import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import { cookies } from "next/headers";
import { api, ApiError, TOKEN_COOKIE } from "@/lib/api";
import { EstadoBadge, PrioridadBadge } from "@/components/Badges";
import { TicketDetailClient } from "./TicketDetailClient";

// Server Component: fetches the ticket on the server (SSR) so the first paint
// already contains the ticket and its comments. The JWT is read from the
// cookie so the SSR request is authenticated.
export default async function TicketDetailPage({
  params,
}: {
  params: { id: string };
}) {
  const id = Number(params.id);
  if (!Number.isInteger(id) || id <= 0) notFound();

  const token = cookies().get(TOKEN_COOKIE)?.value ?? null;
  if (!token) redirect("/login");

  try {
    const ticket = await api.getTicket(id, token);
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
        </div>

        {/* Interactivity (transitions, comments, live updates) on the client. */}
        <TicketDetailClient initial={ticket} />
      </div>
    );
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) notFound();
    if (e instanceof ApiError && (e.status === 401 || e.status === 403)) {
      redirect("/login");
    }
    throw e;
  }
}
