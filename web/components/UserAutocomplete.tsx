/**
 * Selector de usuarios con búsqueda (Autocomplete).
 * 
 * Permite buscar usuarios por email o nombre y seleccionar uno
 * para asignarlo a un ticket. Siempre muestra "Asignarme a mí"
 * como primera opción si hay un usuario autenticado.
 * 
 * Características:
 * - Búsqueda en el servidor con debounce de 250ms
 * - Máximo 5 resultados
 * - Opción "Asignarme a mí" siempre disponible
 * - Se cierra al hacer click fuera
 */
"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "./AuthProvider";
import type { UserOption } from "@/lib/types";

interface Props {
  /** Email del usuario actualmente asignado (para mostrar) */
  currentEmail: string | null;
  /** Callback cuando se selecciona un usuario (null = sin asignar) */
  onSelect: (userId: number | null) => void;
  /** Deshabilitar el selector */
  disabled?: boolean;
  /** Clase CSS para el ancho del contenedor */
  className?: string;
}

/**
 * Componente de autocompletado para seleccionar usuarios.
 * 
 * @example
 * ```tsx
 * <UserAutocomplete
 *   currentEmail={ticket.asignado_a}
 *   onSelect={(userId) => handleAssign(userId)}
 * />
 * ```
 */
export function UserAutocomplete({
  currentEmail,
  onSelect,
  disabled,
  className = "w-72",
}: Props) {
  const { user } = useAuth();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [options, setOptions] = useState<UserOption[]>([]);
  const [loading, setLoading] = useState(false);
  const boxRef = useRef<HTMLDivElement>(null);

  // Cerrar al hacer click fuera del componente
  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (boxRef.current && !boxRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  // Búsqueda en el servidor con debounce cuando el dropdown está abierto
  useEffect(() => {
    if (!open) return;
    setLoading(true);
    const t = setTimeout(() => {
      api
        .listUserOptions(query, 5)
        .then(setOptions)
        .catch(() => setOptions([]))
        .finally(() => setLoading(false));
    }, 250);
    return () => clearTimeout(t);
  }, [open, query]);

  /** Manejar selección de usuario */
  const choose = (id: number | null) => {
    onSelect(id);
    setOpen(false);
    setQuery("");
  };

  return (
    <div ref={boxRef} className={`relative ${className}`}>
      {/* Botón que abre el dropdown */}
      <button
        type="button"
        disabled={disabled}
        onClick={() => setOpen((v) => !v)}
        className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-left text-sm hover:bg-slate-50 disabled:opacity-50"
      >
        {currentEmail ?? <span className="text-slate-400">Sin asignar</span>}
        <span className="float-right text-slate-400">▾</span>
      </button>

      {/* Dropdown con búsqueda y opciones */}
      {open && (
        <div className="absolute z-10 mt-1 w-full rounded-md border border-slate-200 bg-white shadow-lg">
          {/* Campo de búsqueda */}
          <input
            autoFocus
            value={query || currentEmail || ""}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Buscar usuario..."
            className="w-full border-b px-3 py-2 text-sm outline-none"
          />

          {/* Opción "Asignarme a mí" */}
          {user && (
            <button
              type="button"
              onClick={() => choose(user.id)}
              className="w-full px-3 py-2 text-left text-sm hover:bg-blue-50"
            >
              <span className="font-medium text-blue-600">Asignarme a mí</span>
              <span className="ml-2 text-slate-500">({user.email})</span>
            </button>
          )}

          {/* Opción "Sin asignar" */}
          <button
            type="button"
            onClick={() => choose(null)}
            className="w-full border-t px-3 py-2 text-left text-sm text-slate-500 hover:bg-slate-50"
          >
            Sin asignar
          </button>

          {/* Resultados de búsqueda */}
          {loading ? (
            <p className="px-3 py-2 text-sm text-slate-400">Buscando...</p>
          ) : (
            <ul className="max-h-40 overflow-y-auto">
              {options
                .filter((o) => o.id !== user?.id) // No repetir usuario actual
                .map((opt) => (
                  <li key={opt.id}>
                    <button
                      type="button"
                      onClick={() => choose(opt.id)}
                      className="w-full px-3 py-2 text-left text-sm hover:bg-slate-50"
                    >
                      <div className="font-medium">{opt.nombre_completo}</div>
                      <div className="text-slate-500">{opt.email}</div>
                    </button>
                  </li>
                ))}
              {options.length === 0 && query && (
                <li className="px-3 py-2 text-sm text-slate-400">
                  No se encontraron usuarios
                </li>
              )}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
