/**
 * Página de administración de usuarios.
 * 
 * Solo accesible para administradores (RequireAuth con adminOnly).
 * Permite:
 * - Ver la lista de usuarios
 * - Crear nuevos usuarios
 * - Eliminar usuarios existentes
 */
"use client";

import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import type { User } from "@/lib/types";
import { RequireAuth } from "@/components/RequireAuth";
import { PasswordInput } from "@/components/PasswordInput";
import { TableSkeleton, EmptyState, ErrorState } from "@/components/UiStates";

/**
 * Página protegida solo para administradores.
 */
export default function UsersPage() {
  return (
    <RequireAuth adminOnly>
      <UsersAdmin />
    </RequireAuth>
  );
}

/** Estados de carga de la página */
type LoadState = "loading" | "ready" | "error";

/**
 * Panel de administración de usuarios.
 */
function UsersAdmin() {
  // Estado de datos y carga
  const [users, setUsers] = useState<User[]>([]);
  const [state, setState] = useState<LoadState>("loading");
  const [error, setError] = useState("");

  // Campos del formulario de creación
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [nombre, setNombre] = useState("");
  const [apellidos, setApellidos] = useState("");
  const [isAdmin, setIsAdmin] = useState(false);
  const [formError, setFormError] = useState("");
  const [busy, setBusy] = useState(false);

  /**
   * Cargar lista de usuarios desde la API.
   */
  const load = useCallback(async () => {
    setState("loading");
    setError("");
    try {
      setUsers(await api.listUsers());
      setState("ready");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No se pudo cargar");
      setState("error");
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  /**
   * Crear un nuevo usuario.
   * Valida y envía los datos del formulario.
   */
  const createUser = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setFormError("");
    try {
      await api.createUser({
        email: email.trim(),
        password,
        nombre: nombre.trim(),
        apellidos: apellidos.trim(),
        is_admin: isAdmin,
      });
      // Limpiar formulario
      setEmail("");
      setPassword("");
      setNombre("");
      setApellidos("");
      setIsAdmin(false);
      // Recargar lista
      await load();
    } catch (e) {
      setFormError(e instanceof ApiError ? e.message : "No se pudo crear");
    } finally {
      setBusy(false);
    }
  };

  /**
   * Eliminar un usuario tras confirmación.
   */
  const removeUser = async (id: number) => {
    if (!confirm("¿Eliminar este usuario?")) return;
    try {
      await api.deleteUser(id);
      await load();
    } catch (e) {
      alert(e instanceof ApiError ? e.message : "No se pudo eliminar");
    }
  };

  return (
    <div>
      <h1 className="mb-4 text-lg font-semibold">Usuarios</h1>

      {/* Formulario de creación */}
      <form
        onSubmit={createUser}
        className="mb-6 space-y-3 rounded-lg border bg-white p-4"
      >
        <h2 className="text-sm font-medium text-slate-700">Crear usuario</h2>
        <div className="flex flex-wrap gap-3">
          {/* Nombre */}
          <input
            type="text"
            value={nombre}
            onChange={(e) => setNombre(e.target.value)}
            placeholder="Nombre"
            required
            className="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
          {/* Apellidos */}
          <input
            type="text"
            value={apellidos}
            onChange={(e) => setApellidos(e.target.value)}
            placeholder="Apellidos"
            required
            className="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
          {/* Email */}
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="email@empresa.com"
            required
            className="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
          {/* Contraseña */}
          <div className="flex-1">
            <PasswordInput
              value={password}
              onChange={setPassword}
              placeholder="Contraseña (mín. 6)"
              required
              minLength={6}
              className="flex-1"
            />
          </div>
          {/* Checkbox de admin */}
          <label className="flex items-center gap-1 text-sm text-slate-600">
            <input
              type="checkbox"
              checked={isAdmin}
              onChange={(e) => setIsAdmin(e.target.checked)}
            />
            Admin
          </label>
          {/* Botón de crear */}
          <button
            type="submit"
            disabled={busy}
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            Crear
          </button>
        </div>
        {/* Error del formulario */}
        {formError && (
          <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
            {formError}
          </p>
        )}
      </form>

      {/* Estados de carga */}
      {state === "loading" && <TableSkeleton />}
      {state === "error" && <ErrorState mensaje={error} onReintentar={load} />}
      {state === "ready" && users.length === 0 && (
        <EmptyState mensaje="Sin usuarios" />
      )}

      {/* Tabla de usuarios */}
      {state === "ready" && users.length > 0 && (
        <div className="overflow-hidden rounded-lg border bg-white">
          <table className="w-full text-sm">
            <thead className="bg-slate-100 text-left text-slate-600">
              <tr>
                <th className="px-4 py-2 font-medium">Nombre</th>
                <th className="px-4 py-2 font-medium">Email</th>
                <th className="px-4 py-2 font-medium">Rol</th>
                <th className="px-4 py-2 font-medium"></th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} className="border-t">
                  <td className="px-4 py-2">{u.nombre_completo}</td>
                  <td className="px-4 py-2">{u.email}</td>
                  <td className="px-4 py-2">
                    {u.is_admin ? "Administrador" : "Agente"}
                  </td>
                  <td className="px-4 py-2 text-right">
                    <button
                      onClick={() => removeUser(u.id)}
                      className="text-sm text-red-600 hover:underline"
                    >
                      Eliminar
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
