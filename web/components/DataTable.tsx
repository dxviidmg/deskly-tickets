"use client";

import { useState } from "react";

export interface Column<T> {
  key: keyof T | string;
  header: string;
  render?: (value: unknown, row: T) => React.ReactNode;
  className?: string;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  rowKey: (row: T) => string | number;
  loading?: boolean;
  emptyMessage?: string;
  onRowClick?: (row: T) => void;
  flashRow?: (row: T) => boolean;
}

export function DataTable<T>({
  columns,
  data,
  rowKey,
  loading = false,
  emptyMessage = "No hay datos",
  onRowClick,
  flashRow,
}: DataTableProps<T>) {
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

  if (data.length === 0) {
    return (
      <p className="py-8 text-center text-slate-500">{emptyMessage}</p>
    );
  }

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
