/**
 * Provider de React Query para la aplicación.
 * 
 * Configura QueryClient con opciones sensibles:
 * - staleTime: 1 minuto (los datos se consideran frescos)
 * - refetchOnWindowFocus: desactivado (no refetch al cambiar de pestaña)
 * 
 * Debe envolver la aplicación en layout.tsx.
 */
"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";

/**
 * Provider que configura React Query.
 * 
 * Usa useState para crear el QueryClient solo una vez
 * (evita recrearlo en cada render).
 */
export function QueryProvider({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60 * 1000, // 1 minuto
            refetchOnWindowFocus: false,
          },
        },
      })
  );

  return (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}
