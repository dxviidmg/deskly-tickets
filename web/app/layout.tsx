import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Deskly — Tickets de soporte",
  description: "Panel de tickets de soporte",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="es">
      <body>
        <header className="border-b bg-white">
          <div className="mx-auto max-w-5xl px-4 py-4">
            <Link href="/" className="text-xl font-semibold">
              Deskly
            </Link>
            <span className="ml-2 text-sm text-slate-500">
              Tickets de soporte
            </span>
          </div>
        </header>
        <main className="mx-auto max-w-5xl px-4 py-6">{children}</main>
      </body>
    </html>
  );
}
