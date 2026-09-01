"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "./AuthProvider";
import type { UserOption } from "@/lib/types";

interface Props {
  currentEmail: string | null; // email currently assigned (for display)
  onSelect: (userId: number | null) => void;
  disabled?: boolean;
  /** Width utility class for the container. Defaults to a fixed width. */
  className?: string;
}

/**
 * Searchable user picker (Autocomplete). Shows up to 5 users, queries the
 * backend as you type, and always offers "Asignarme a mí" as the first option.
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

  // Close on outside click.
  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (boxRef.current && !boxRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  // Debounced server-side search whenever the dropdown is open or query changes.
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

  const choose = (id: number | null) => {
    onSelect(id);
    setOpen(false);
    setQuery("");
  };

  return (
    <div ref={boxRef} className={`relative ${className}`}>
      <button
        type="button"
        disabled={disabled}
        onClick={() => setOpen((v) => !v)}
        className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-left text-sm hover:bg-slate-50 disabled:opacity-50"
      >
        {currentEmail ?? <span className="text-slate-400">Sin asignar</span>}
        <span className="float-right text-slate-400">▾</span>
      </button>

      {open && (
        <div className="absolute z-10 mt-1 w-full rounded-md border border-slate-200 bg-white shadow-lg">
          <input
            autoFocus
            value={query || currentEmail || ""}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Buscar por email…"
            className="w-full rounded-t-md border-b border-slate-200 px-3 py-2 text-sm outline-none"
          />
          <ul className="max-h-56 overflow-auto py-1 text-sm">
            {/* First option: assign to the current user. */}
            {user && (
              <li>
                <button
                  type="button"
                  onClick={() => choose(user.id)}
                  className="block w-full px-3 py-1.5 text-left font-medium text-blue-700 hover:bg-blue-50"
                >
                  Asignarme a mí ({user.email})
                </button>
              </li>
            )}
            {/* Option to clear the assignee. */}
            <li>
              <button
                type="button"
                onClick={() => choose(null)}
                className="block w-full px-3 py-1.5 text-left text-slate-500 hover:bg-slate-50"
              >
                Sin asignar
              </button>
            </li>
            <li className="my-1 border-t border-slate-100" />
            {loading && (
              <li className="px-3 py-1.5 text-slate-400">Buscando…</li>
            )}
            {!loading && options.length === 0 && (
              <li className="px-3 py-1.5 text-slate-400">Sin resultados</li>
            )}
            {!loading &&
              options.map((o) => (
                <li key={o.id}>
                  <button
                    type="button"
                    onClick={() => choose(o.id)}
                    className="block w-full px-3 py-1.5 text-left hover:bg-slate-50"
                  >
                    <span className="font-medium">{o.nombre_completo}</span>
                    <span className="ml-2 text-xs text-slate-400">
                      {o.email}
                    </span>
                  </button>
                </li>
              ))}
          </ul>
        </div>
      )}
    </div>
  );
}
