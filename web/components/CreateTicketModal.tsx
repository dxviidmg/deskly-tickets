/**
 * Modal para crear un ticket desde el listado.
 *
 * Muestra un formulario (título, descripción y prioridad) dentro del componente
 * `Modal` genérico. Valida con Zod + react-hook-form (`ticketCreateSchema`) y,
 * al enviar, crea el ticket vía `api.createTicket`.
 *
 * Decisión de diseño: los tickets se crean **sin asignar**
 * (`asignado_a_id = null`), igual que los que entran por webhook. Un agente se
 * asigna después desde el listado o el detalle. Por eso el formulario no incluye
 * selector de usuario.
 *
 * @example
 * ```tsx
 * <CreateTicketModal
 *   open={open}
 *   onClose={() => setOpen(false)}
 *   onCreated={(ticket) => refrescarLista()}
 * />
 * ```
 */
"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { toast } from "sonner";

import { Modal } from "./Modal";
import { api, ApiError } from "@/lib/api";
import { ticketCreateSchema, TicketCreateInput } from "@/lib/schemas";
import { PRIORIDADES, PRIORIDADES_LABELS } from "@/lib/constants";
import type { Ticket } from "@/lib/types";

interface Props {
  /** Controla la visibilidad del modal */
  open: boolean;
  /** Cierra el modal (sin crear nada) */
  onClose: () => void;
  /** Se invoca con el ticket recién creado para que el listado se actualice */
  onCreated: (ticket: Ticket) => void;
}

/**
 * Formulario de creación de ticket dentro de un modal.
 *
 * @param open - Si el modal está visible
 * @param onClose - Callback para cerrar el modal
 * @param onCreated - Callback tras crear con éxito (recibe el ticket)
 */
export function CreateTicketModal({ open, onClose, onCreated }: Props) {
  // Error general de la petición (distinto de los errores de validación)
  const [error, setError] = useState("");

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<TicketCreateInput>({
    resolver: zodResolver(ticketCreateSchema),
    defaultValues: { titulo: "", descripcion: "", prioridad: "media" },
  });

  /** Cierra el modal y limpia formulario + error. */
  const handleClose = () => {
    reset();
    setError("");
    onClose();
  };

  /**
   * Envía el formulario: crea el ticket sin asignar, avisa con un toast,
   * limpia el formulario y notifica al padre para refrescar la lista.
   */
  const onSubmit = async (data: TicketCreateInput) => {
    setError("");
    try {
      // Se crea sin asignar: solo enviamos título, descripción y prioridad.
      const ticket = await api.createTicket({
        titulo: data.titulo.trim(),
        descripcion: data.descripcion.trim(),
        prioridad: data.prioridad,
      });
      toast.success("Ticket creado");
      reset();
      onCreated(ticket);
      onClose();
    } catch (e) {
      setError(
        e instanceof ApiError ? e.message : "No se pudo crear el ticket"
      );
    }
  };

  return (
    <Modal open={open} onClose={handleClose} title="Nuevo ticket">
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-3">
        {/* Campo: título */}
        <div>
          <label htmlFor="titulo" className="mb-1 block text-sm text-slate-600">
            Título
          </label>
          <input
            id="titulo"
            {...register("titulo")}
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
          {errors.titulo && (
            <p className="mt-1 text-sm text-red-600">{errors.titulo.message}</p>
          )}
        </div>

        {/* Campo: descripción */}
        <div>
          <label
            htmlFor="descripcion"
            className="mb-1 block text-sm text-slate-600"
          >
            Descripción
          </label>
          <textarea
            id="descripcion"
            rows={4}
            {...register("descripcion")}
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
          {errors.descripcion && (
            <p className="mt-1 text-sm text-red-600">
              {errors.descripcion.message}
            </p>
          )}
        </div>

        {/* Campo: prioridad */}
        <div>
          <label
            htmlFor="prioridad"
            className="mb-1 block text-sm text-slate-600"
          >
            Prioridad
          </label>
          <select
            id="prioridad"
            {...register("prioridad")}
            className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm"
          >
            {PRIORIDADES.map((p) => (
              <option key={p} value={p}>
                {PRIORIDADES_LABELS[p]}
              </option>
            ))}
          </select>
        </div>

        {/* Error general de la petición */}
        {error && (
          <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </p>
        )}

        {/* Acciones */}
        <div className="flex justify-end gap-2 pt-2">
          <button
            type="button"
            onClick={handleClose}
            className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm hover:bg-slate-50"
          >
            Cancelar
          </button>
          <button
            type="submit"
            disabled={isSubmitting}
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {isSubmitting ? "Creando…" : "Crear ticket"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
