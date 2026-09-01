import type { Metadata } from "next";
import "./globals.css";
import { Toaster } from "sonner";
import { AuthProvider } from "@/components/AuthProvider";
import { NavBar } from "@/components/NavBar";
import { QueryProvider } from "@/components/QueryProvider";

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
        <QueryProvider>
          <AuthProvider>
            <Toaster richColors position="top-right" />
            <NavBar />
            <main className="mx-auto max-w-5xl px-4 py-6">{children}</main>
          </AuthProvider>
        </QueryProvider>
      </body>
    </html>
  );
}
