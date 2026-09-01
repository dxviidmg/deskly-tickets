/**
 * Schemas de validación con Zod para formularios.
 * 
 * Define schemas para:
 * - Login: validación de email y contraseña
 * - Usuarios: creación de usuarios
 * - Tickets: creación y actualización
 * - Comentarios: cuerpo del comentario
 * 
 * Cada schema exporta también su tipo inferido para usar en
 * react-hook-form y otras partes de la aplicación.
 */
import { z } from "zod";

// --- Schemas de autenticación ---

/** Schema para el formulario de login */
export const loginSchema = z.object({
  email: z.string().email("Email inválido"),
  password: z.string().min(1, "Contraseña requerida"),
});

/** Tipo inferido del schema de login */
export type LoginInput = z.infer<typeof loginSchema>;

// --- Schemas de usuarios ---

/** Schema para crear un usuario nuevo */
export const userCreateSchema = z.object({
  email: z.string().email("Email inválido"),
  password: z.string().min(6, "Mínimo 6 caracteres").max(128),
  nombre: z.string().min(1, "Nombre requerido").max(120),
  apellidos: z.string().min(1, "Apellidos requeridos").max(120),
  is_admin: z.boolean(),
});

/** Tipo inferido del schema de creación de usuario */
export type UserCreateInput = z.infer<typeof userCreateSchema>;

// --- Schemas de tickets ---

/** Schema para crear un ticket nuevo */
export const ticketCreateSchema = z.object({
  titulo: z.string().min(1, "Título requerido").max(200),
  descripcion: z.string().min(1, "Descripción requerida"),
  prioridad: z.enum(["baja", "media", "alta", "urgente"]).optional(),
  asignado_a_id: z.number().nullable().optional(),
});

/** Schema para actualizar un ticket (todos los campos opcionales) */
export const ticketUpdateSchema = z.object({
  titulo: z.string().min(1).max(200).optional(),
  descripcion: z.string().min(1).optional(),
  prioridad: z.enum(["baja", "media", "alta", "urgente"]).optional(),
  asignado_a_id: z.number().nullable().optional(),
});

/** Schema para añadir un comentario */
export const commentSchema = z.object({
  cuerpo: z.string().min(1, "Comentario requerido"),
});

/** Tipos inferidos de los schemas de tickets */
export type TicketCreateInput = z.infer<typeof ticketCreateSchema>;
export type TicketUpdateInput = z.infer<typeof ticketUpdateSchema>;
export type CommentInput = z.infer<typeof commentSchema>;
