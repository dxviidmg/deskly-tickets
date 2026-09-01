"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "./AuthProvider";

/**
 * Guards a client page: redirects to /login when there is no authenticated
 * user. If `adminOnly` is set, non-admins are sent back to the dashboard.
 */
export function RequireAuth({
  children,
  adminOnly = false,
}: {
  children: React.ReactNode;
  adminOnly?: boolean;
}) {
  const { user, loading, sessionExpired } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (loading) return;
    if (!user) {
      // Si la sesión expiró, redirige a login con un parámetro para mostrar el aviso
      const redirectTo = sessionExpired ? "/login?reason=session_expired" : "/login";
      router.replace(redirectTo);
    } else if (adminOnly && !user.is_admin) {
      router.replace("/");
    }
  }, [loading, user, adminOnly, router, sessionExpired]);

  if (loading) {
    return <p className="text-sm text-slate-500">Cargando…</p>;
  }
  if (!user || (adminOnly && !user.is_admin)) {
    return null; // redirecting
  }
  return <>{children}</>;
}
