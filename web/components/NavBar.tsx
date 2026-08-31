"use client";

import Link from "next/link";
import { useAuth } from "./AuthProvider";

export function NavBar() {
  const { user, logout } = useAuth();

  return (
    <header className="border-b bg-white">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-4">
        <div>
          <Link href="/" className="text-xl font-semibold">
            Deskly
          </Link>
          <span className="ml-2 text-sm text-slate-500">
            Tickets de soporte
          </span>
        </div>
        {user && (
          <nav className="flex items-center gap-4 text-sm">
            <Link href="/" className="text-slate-600 hover:underline">
              Tickets
            </Link>
            {user.is_admin && (
              <Link href="/users" className="text-slate-600 hover:underline">
                Usuarios
              </Link>
            )}
            <span className="text-slate-400">|</span>
            <span className="text-slate-600">{user.email}</span>
            <button
              onClick={logout}
              className="rounded-md border border-slate-300 px-2 py-1 text-slate-700 hover:bg-slate-50"
            >
              Salir
            </button>
          </nav>
        )}
      </div>
    </header>
  );
}
