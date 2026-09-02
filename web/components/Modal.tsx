/**
 * Modal genérico reutilizable.
 *
 * Componente de presentación que muestra un cuadro de diálogo centrado sobre
 * un overlay semitransparente. No conoce su contenido: recibe `children`, así
 * que sirve para cualquier formulario o mensaje (p. ej. crear ticket).
 *
 * Accesibilidad y UX:
 * - Se cierra con la tecla `Escape`, con el botón de cierre o al hacer clic
 *   fuera del cuadro (en el overlay).
 * - Bloquea el scroll del `body` mientras está abierto para evitar que el
 *   fondo se desplace.
 * - Usa `role="dialog"` y `aria-modal` para lectores de pantalla.
 *
 * @example
 * ```tsx
 * <Modal open={open} onClose={() => setOpen(false)} title="Nuevo ticket">
 *   <MiFormulario />
 * </Modal>
 * ```
 */
"use client";

import { useEffect } from "react";

interface Props {
  /** Si es true, el modal se muestra */
  open: boolean;
  /** Callback para cerrar el modal (Escape, botón o clic en overlay) */
  onClose: () => void;
  /** Título mostrado en la cabecera del modal */
  title: string;
  /** Contenido del modal (formulario, mensaje, etc.) */
  children: React.ReactNode;
}

/**
 * Cuadro de diálogo modal controlado por el componente padre.
 *
 * @param open - Controla la visibilidad
 * @param onClose - Se invoca cuando el usuario pide cerrar
 * @param title - Título de la cabecera
 * @param children - Contenido a renderizar dentro del modal
 */
export function Modal({ open, onClose, title, children }: Props) {
  // Cerrar con la tecla Escape y bloquear el scroll del fondo mientras
  // el modal está abierto. Ambos efectos se limpian al cerrar/desmontar.
  useEffect(() => {
    if (!open) return;

    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKeyDown);

    // Guardar y bloquear el overflow del body
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = previousOverflow;
    };
  }, [open, onClose]);

  // No renderizar nada si está cerrado
  if (!open) return null;

  return (
    // Overlay: al hacer clic aquí (fuera del cuadro) se cierra
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      onClick={onClose}
    >
      {/* Cuadro de diálogo: stopPropagation evita que el clic interno cierre */}
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className="w-full max-w-md rounded-lg bg-white shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Cabecera con título y botón de cierre */}
        <div className="flex items-center justify-between border-b px-5 py-3">
          <h2 className="text-base font-semibold">{title}</h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Cerrar"
            className="rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
          >
            ✕
          </button>
        </div>

        {/* Contenido */}
        <div className="p-5">{children}</div>
      </div>
    </div>
  );
}
