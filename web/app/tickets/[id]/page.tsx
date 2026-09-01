import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import { cookies } from "next/headers";
import { api, ApiError, TOKEN_COOKIE } from "@/lib/api";
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

        {/* Order, transitions, comments and live updates on the client.
            The status/assignee section renders above the title/description. */}
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
