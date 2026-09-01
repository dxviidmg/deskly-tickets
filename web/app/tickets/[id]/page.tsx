/**
 * Página de detalle de ticket (Server Component).
 * 
 * Renderiza el ticket en el servidor (SSR) para que el primer pintado
 * ya contenga los datos. El JWT se lee de la cookie para autenticar
 * la petición SSR.
 * 
 * Flujo:
 * 1. Valida el ID del ticket
 * 2. Verifica autenticación (cookie JWT)
 * 3. Obtiene el ticket desde la API
 * 4. Pasa los datos al componente cliente para interactividad
 */

import { notFound, redirect } from "next/navigation";
import { cookies } from "next/headers";
import { api, ApiError, TOKEN_COOKIE } from "@/lib/api";
import { TicketDetailClient } from "./TicketDetailClient";

/**
 * Página de detalle renderizada en el servidor.
 * 
 * @param params - Parámetros de la URL (id del ticket)
 */
export default async function TicketDetailPage({
  params,
}: {
  params: { id: string };
}) {
  // Validar que el ID sea un entero positivo
  const id = Number(params.id);
  if (!Number.isInteger(id) || id <= 0) notFound();

  // Verificar autenticación
  const token = cookies().get(TOKEN_COOKIE)?.value ?? null;
  if (!token) redirect("/login");

  try {
    // Obtener el ticket con comentarios y historial
    const ticket = await api.getTicket(id, token);
    return (
      <div>
        <TicketDetailClient initial={ticket} />
      </div>
    );
  } catch (e) {
    // Manejar errores específicos
    if (e instanceof ApiError && e.status === 404) notFound();
    if (e instanceof ApiError && (e.status === 401 || e.status === 403)) {
      redirect("/login");
    }
    // Otros errores: lanzar para que los maneje error.tsx
    throw e;
  }
}
