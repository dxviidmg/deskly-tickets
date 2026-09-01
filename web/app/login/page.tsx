"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/components/AuthProvider";
import { PasswordInput } from "@/components/PasswordInput";
import { ApiError } from "@/lib/api";

function LoginForm() {
  const { login, clearSessionExpired } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  // Si viene reason=session_expired, mostrar aviso
  useEffect(() => {
    if (searchParams.get("reason") === "session_expired") {
      setError("Sesión caducada. Inicia de nuevo sesión.");
      clearSessionExpired();
    }
  }, [searchParams, clearSessionExpired]);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await login(email.trim(), password);
      router.push("/");
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "No se pudo iniciar sesión"
      );
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mx-auto max-w-sm">
      <h1 className="mb-4 text-lg font-semibold">Iniciar sesión</h1>
      <form
        onSubmit={onSubmit}
        className="space-y-3 rounded-lg border bg-white p-5"
      >
        <div>
          <label className="mb-1 block text-sm text-slate-600">Email</label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label className="mb-1 block text-sm text-slate-600">
            Contraseña
          </label>
          <PasswordInput
            value={password}
            onChange={setPassword}
            placeholder="Contraseña"
            required
          />
        </div>
        {error && (
          <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </p>
        )}
        <button
          type="submit"
          disabled={busy}
          className="w-full rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {busy ? "Entrando…" : "Entrar"}
        </button>
      </form>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <div className="mx-auto max-w-sm">
          <p className="text-slate-500">Cargando…</p>
        </div>
      }
    >
      <LoginForm />
    </Suspense>
  );
}
