"use client";

import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import type { User } from "@/lib/types";
import { RequireAuth } from "@/components/RequireAuth";
import { TableSkeleton, EmptyState, ErrorState } from "@/components/UiStates";

export default function UsersPage() {
  return (
    <RequireAuth adminOnly>
      <UsersAdmin />
    </RequireAuth>
  );
}

type LoadState = "loading" | "ready" | "error";

function UsersAdmin() {
  const [users, setUsers] = useState<User[]>([]);
  const [state, setState] = useState<LoadState>("loading");
  const [error, setError] = useState("");

  // Create form
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isAdmin, setIsAdmin] = useState(false);
  const [formError, setFormError] = useState("");
  const [busy, setBusy] = useState(false);

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

  const createUser = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setFormError("");
    try {
      await api.createUser(email.trim(), password, isAdmin);
      setEmail("");
      setPassword("");
      setIsAdmin(false);
      await load();
    } catch (e) {
      setFormError(e instanceof ApiError ? e.message : "No se pudo crear");
    } finally {
      setBusy(false);
    }
  };

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

      {/* Create form */}
      <form
        onSubmit={createUser}
        className="mb-6 space-y-3 rounded-lg border bg-white p-4"
      >
        <h2 className="text-sm font-medium text-slate-700">Crear usuario</h2>
        <div className="flex flex-wrap gap-3">
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="email@empresa.com"
            required
            className="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Contraseña (mín. 6)"
            required
            minLength={6}
            className="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
          <label className="flex items-center gap-1 text-sm text-slate-600">
            <input
              type="checkbox"
              checked={isAdmin}
              onChange={(e) => setIsAdmin(e.target.checked)}
            />
            Admin
          </label>
          <button
            type="submit"
            disabled={busy}
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            Crear
          </button>
        </div>
        {formError && (
          <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
            {formError}
          </p>
        )}
      </form>

      {state === "loading" && <TableSkeleton />}
      {state === "error" && <ErrorState mensaje={error} onReintentar={load} />}
      {state === "ready" && users.length === 0 && (
        <EmptyState mensaje="Sin usuarios" />
      )}
      {state === "ready" && users.length > 0 && (
        <div className="overflow-hidden rounded-lg border bg-white">
          <table className="w-full text-sm">
            <thead className="bg-slate-100 text-left text-slate-600">
              <tr>
                <th className="px-4 py-2 font-medium">Email</th>
                <th className="px-4 py-2 font-medium">Rol</th>
                <th className="px-4 py-2 font-medium"></th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} className="border-t">
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
