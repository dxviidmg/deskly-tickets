import { z } from "zod";

// Auth schemas
export const loginSchema = z.object({
  email: z.string().email("Email inválido"),
  password: z.string().min(1, "Contraseña requerida"),
});

export type LoginInput = z.infer<typeof loginSchema>;

// User schemas
export const userCreateSchema = z.object({
  email: z.string().email("Email inválido"),
  password: z.string().min(6, "Mínimo 6 caracteres").max(128),
  nombre: z.string().min(1, "Nombre requerido").max(120),
  apellidos: z.string().min(1, "Apellidos requeridos").max(120),
  is_admin: z.boolean(),
});

export type UserCreateInput = z.infer<typeof userCreateSchema>;

// Ticket schemas
export const ticketCreateSchema = z.object({
  titulo: z.string().min(1, "Título requerido").max(200),
  descripcion: z.string().min(1, "Descripción requerida"),
  prioridad: z.enum(["baja", "media", "alta", "urgente"]).optional(),
  asignado_a_id: z.number().nullable().optional(),
});

export const ticketUpdateSchema = z.object({
  titulo: z.string().min(1).max(200).optional(),
  descripcion: z.string().min(1).optional(),
  prioridad: z.enum(["baja", "media", "alta", "urgente"]).optional(),
  asignado_a_id: z.number().nullable().optional(),
});

export const commentSchema = z.object({
  cuerpo: z.string().min(1, "Comentario requerido"),
});

export type TicketCreateInput = z.infer<typeof ticketCreateSchema>;
export type TicketUpdateInput = z.infer<typeof ticketUpdateSchema>;
export type CommentInput = z.infer<typeof commentSchema>;
