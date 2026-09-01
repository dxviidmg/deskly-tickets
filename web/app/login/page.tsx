/**
 * Página de inicio de sesión.
 * 
 * Permite a los usuarios autenticarse con email y contraseña.
 * Valida el formulario con Zod y react-hook-form.
 * 
 * Casos especiales:
 * - Si la sesión expiró, muestra un mensaje al usuario
 * - Redirige al dashboard tras login exitoso
 */
"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

import { useAuth } from "@/components/AuthProvider";
import { PasswordInput } from "@/components/PasswordInput";
import { ApiError } from "@/lib/api";
import { loginSchema, LoginInput } from "@/lib/schemas";

/**
 * Formulario de login separado para poder usar useSearchParams
 * dentro de un Suspense boundary.
 */
function LoginForm() {
  const { login, clearSessionExpired } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  // Configuración de react-hook-form con validación Zod
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginInput>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "" },
  });

  // Mostrar aviso si la sesión expiró (redirigido desde RequireAuth)
  useEffect(() => {
    if (searchParams.get("reason") === "session_expired") {
      setError("Sesión caducada. Inicia de nuevo sesión.");
      clearSessionExpired();
    }
  }, [searchParams, clearSessionExpired]);

  /**
   * Manejar envío del formulario.
   * Intenta autenticar y redirige al dashboard si tiene éxito.
   */
  const onSubmit = async (data: LoginInput) => {
    setBusy(true);
    setError("");
    try {
      await login(data.email.trim(), data.password);
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
        onSubmit={handleSubmit(onSubmit)}
        className="space-y-3 rounded-lg border bg-white p-5"
      >
        {/* Campo de email */}
        <div>
          <label className="mb-1 block text-sm text-slate-600">Email</label>
          <input
            type="email"
            {...register("email")}
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
          {errors.email && (
            <p className="mt-1 text-sm text-red-600">{errors.email.message}</p>
          )}
        </div>

        {/* Campo de contraseña */}
        <div>
          <label className="mb-1 block text-sm text-slate-600">
            Contraseña
          </label>
          <PasswordInput
            {...register("password")}
            placeholder="Contraseña"
          />
          {errors.password && (
            <p className="mt-1 text-sm text-red-600">{errors.password.message}</p>
          )}
        </div>

        {/* Mensaje de error general */}
        {error && (
          <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </p>
        )}

        {/* Botón de envío */}
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

/**
 * Página de login con Suspense para useSearchParams.
 * 
 * El Suspense es necesario porque useSearchParams requiere
 * que el componente se renderice en el cliente.
 */
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
