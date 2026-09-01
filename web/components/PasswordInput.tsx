/**
 * Campo de contraseña con botón para mostrar/ocultar.
 * 
 * Permite alternar entre texto visible y oculto (asteriscos)
 * para que el usuario pueda verificar lo que escribe.
 */

import { useState } from "react";
import type { InputHTMLAttributes } from "react";

/**
 * Props del campo de contraseña.
 * Extiende los atributos estándar de input para ser compatible con react-hook-form.
 */
interface PasswordInputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "type"> {
  /** Valor actual de la contraseña */
  value?: string;
  /** Callback cuando cambia el valor */
  onChange?: (e: React.ChangeEvent<HTMLInputElement>) => void;
}

/**
 * Input de contraseña con toggle de visibilidad.
 * 
 * @example
 * ```tsx
 * <PasswordInput
 *   value={password}
 *   onChange={(e) => setPassword(e.target.value)}
 *   placeholder="Tu contraseña"
 *   required
 * />
 * ```
 */
export function PasswordInput({
  value,
  onChange,
  placeholder = "Contraseña",
  required = false,
  disabled = false,
  minLength,
  className = "",
  ...rest
}: PasswordInputProps) {
  const [showPassword, setShowPassword] = useState(false);

  const toggleVisibility = () => {
    setShowPassword(!showPassword);
  };

  return (
    <div className="relative flex items-center">
      <input
        type={showPassword ? "text" : "password"}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        required={required}
        disabled={disabled}
        minLength={minLength}
        className={`w-full rounded-md border border-slate-300 px-3 py-2 text-sm pr-10 ${className}`}
        {...rest}
      />
      <button
        type="button"
        onClick={toggleVisibility}
        disabled={disabled}
        aria-label={showPassword ? "Ocultar contraseña" : "Mostrar contraseña"}
        className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 text-slate-500 hover:bg-slate-100 hover:text-slate-700 disabled:opacity-50"
        title={showPassword ? "Ocultar" : "Mostrar"}
      >
        {showPassword ? (
          // Icono de ojo abierto (contraseña visible)
          <svg
            className="h-4 w-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
            />
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
            />
          </svg>
        ) : (
          // Icono de ojo tachado (contraseña oculta)
          <svg
            className="h-4 w-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21"
            />
          </svg>
        )}
      </button>
    </div>
  );
}
