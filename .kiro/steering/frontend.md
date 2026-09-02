# Frontend (Next.js)

Ubicación: `web/`. Stack real: Next.js 14 (App Router), React 18, TypeScript 5,
TanStack Query 5, react-hook-form + Zod, sonner, Tailwind.

## Estructura

- **`app/`**: App Router (páginas, `layout.tsx`, `error.tsx`, `not-found.tsx`).
- **`components/`**: componentes reutilizables (DataTable, Badges, providers, etc.).
- **`hooks/`**: hooks (p. ej. `useTicketStream.ts` para WebSocket).
- **`lib/`**: `api.ts` (cliente HTTP tipado, SSR-aware), `schemas.ts` (Zod),
  `types.ts` (tipos), `constants.ts` (labels/colores).

## Server vs Client Components

- Por defecto en App Router los componentes son **Server Components**.
- Marcar `"use client"` solo cuando se necesite interactividad, estado, efectos o
  hooks del navegador (formularios, WebSocket, TanStack Query).
- El detalle de ticket usa **SSR**; el dashboard es interactivo (cliente).

## Estado del servidor (TanStack Query)

- Usar TanStack Query para datos del servidor (fetch, cache, invalidación). No
  duplicar ese estado en `useState`.
- Envolver con `QueryProvider`. Invalidar queries tras mutaciones para refrescar.

## Formularios y validación

- react-hook-form + Zod (`lib/schemas.ts`). Los inputs reutilizables deben
  reenviar `ref` (usar `forwardRef`) para que react-hook-form lea el valor.

## Config

- URLs solo desde `process.env` (ver `web/.env.example`); sin URLs hardcodeadas.
- `NEXT_PUBLIC_*` son **build-time** (se hornean en el bundle); `API_INTERNAL_URL`
  es runtime del SSR.
- Existe `openapi-typescript` (`npm run types:gen`) para generar tipos desde el
  OpenAPI del backend; preferirlo sobre tipos manuales cuando aplique.
