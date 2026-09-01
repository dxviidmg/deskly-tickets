/**
 * Componente de protección de rutas.
 * 
 * Protege páginas que requieren autenticación:
 * - Redirige a /login si no hay usuario autenticado
 * - Si la sesión expiró, redirige con parámetro para mostrar aviso
 * - Si adminOnly=true, redirige a inicio si el usuario no es admin
 * 
 * @example
 * ```tsx
 * // Página que requiere autenticación
 * <RequireAuth>
 *   <Dashboard />
 * </RequireAuth>
 * 
 * // Página solo para administradores
 * <RequireAuth adminOnly>
 *   <UsersAdmin />
 * </RequireAuth>
 * ```
 */
"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "./AuthProvider";

interface Props {
  children: React.ReactNode;
  /** Si es true, solo administradores pueden acceder */
  adminOnly?: boolean;
}

/**
 * Guard que protege páginas según autenticación y permisos.
 * 
 * Muestra "Cargando..." mientras verifica el estado de autenticación.
 * Redirige según corresponda si el usuario no tiene acceso.
 */
export function RequireAuth({ children, adminOnly = false }: Props) {
  const { user, loading, sessionExpired } = useAuth();
  const router = useRouter();

  useEffect(() => {
    // Esperar a que termine la carga inicial
    if (loading) return;

    // Sin usuario: redirigir a login
    if (!user) {
      const redirectTo = sessionExpired 
        ? "/login?reason=session_expired" 
        : "/login";
      router.replace(redirectTo);
    } 
    // Usuario sin permisos de admin en página protegida
    else if (adminOnly && !user.is_admin) {
      router.replace("/");
    }
  }, [loading, user, adminOnly, router, sessionExpired]);

  // Estado de carga
  if (loading) {
    return <p className="text-sm text-slate-500">Cargando…</p>;
  }

  // Sin acceso (mientras redirige)
  if (!user || (adminOnly && !user.is_admin)) {
    return null;
  }

  // Usuario con acceso: renderizar contenido
  return <>{children}</>;
}
