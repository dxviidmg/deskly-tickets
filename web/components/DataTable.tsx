/**
 * Tabla de datos abstracta y reutilizable.
 * 
 * Componente genérico que renderiza una tabla con:
 * - Estados de carga (skeleton)
 * - Estado vacío (mensaje configurable)
 * - Columnas configurables con renderizado personalizado
 * - Soporte para click en filas
 * - Animación de highlight para filas actualizadas
 * 
 * @example
 * ```tsx
 * <DataTable
 *   columns={[
 *     { key: "titulo", header: "Título" },
 *     { key: "estado", header: "Estado", render: (v) => <Badge>{v}</Badge> },
 *   ]}
 *   data={tickets}
 *   rowKey={(t) => t.id}
 *   loading={isLoading}
 * />
 * ```
 */
"use client";

import { useState } from "react";

/** Definición de una columna de la tabla */
export interface Column<T> {
  /** Clave del campo o ruta con puntos (ej: "asignado.email") */
  key: keyof T | string;
  /** Texto del encabezado */
  header: string;
  /** Función de renderizado personalizado */
  render?: (value: unknown, row: T) => React.ReactNode;
  /** Clases CSS adicionales para la celda */
  className?: string;
}

interface DataTableProps<T> {
  /** Definición de columnas */
  columns: Column<T>[];
  /** Datos a mostrar */
  data: T[];
  /** Función para obtener la clave única de cada fila */
  rowKey: (row: T) => string | number;
  /** Mostrar estado de carga */
  loading?: boolean;
  /** Mensaje cuando no hay datos */
  emptyMessage?: string;
  /** Callback al hacer click en una fila */
  onRowClick?: (row: T) => void;
  /** Función para determinar si una fila debe brillar (highlight) */
  flashRow?: (row: T) => boolean;
}

/**
 * Componente de tabla genérico.
 * 
 * Renderiza una tabla HTML con estilos Tailwind, soporte para
 * carga, vacío, y highlight visual.
 */
export function DataTable<T>({
  columns,
  data,
  rowKey,
  loading = false,
  emptyMessage = "No hay datos",
  onRowClick,
  flashRow,
}: DataTableProps<T>) {
  // Estado de carga: mostrar skeleton
  if (loading) {
    return (
      <div className="space-y-2">
        {[...Array(5)].map((_, i) => (
          <div
            key={i}
            className="h-12 animate-pulse rounded-lg bg-slate-100"
          />
        ))}
      </div>
    );
  }

  // Estado vacío: mostrar mensaje
  if (data.length === 0) {
    return (
      <p className="py-8 text-center text-slate-500">{emptyMessage}</p>
    );
  }

  // Renderizar tabla con datos
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b bg-slate-50">
            {columns.map((col) => (
              <th
                key={String(col.key)}
                className={`px-3 py-2 font-medium text-slate-600 ${col.className || ""}`}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row) => {
            const key = rowKey(row);
            const isFlashing = flashRow ? flashRow(row) : false;
            return (
              <tr
                key={key}
                onClick={() => onRowClick?.(row)}
                className={`border-b hover:bg-slate-50 ${
                  onRowClick ? "cursor-pointer" : ""
                } ${isFlashing ? "ticket-row-flash" : ""}`}
              >
                {columns.map((col) => {
                  // Obtener el valor de la celda (soporta rutas con puntos)
                  const value =
                    typeof col.key === "string" && col.key.includes(".")
                      ? col.key.split(".").reduce((obj: unknown, k) => {
                          if (obj && typeof obj === "object" && k in obj) {
                            return (obj as Record<string, unknown>)[k];
                          }
                          return undefined;
                        }, row)
                      : (row as Record<string, unknown>)[col.key as string];
                  return (
                    <td
                      key={String(col.key)}
                      className={`px-3 py-2 ${col.className || ""}`}
                    >
                      {col.render ? col.render(value, row) : String(value ?? "")}
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
