import { useId, type ReactElement, cloneElement } from "react";

import { cn } from "@/lib/cn";

interface FieldProps {
  label: string;
  error?: string;
  hint?: string;
  required?: boolean;
  className?: string;
  children: ReactElement<{ id?: string; "aria-invalid"?: boolean; "aria-describedby"?: string }>;
}

/**
 * Labelled form control. Wires up id, aria-invalid and aria-describedby so the
 * error text is announced rather than only being visible.
 */
export function Field({ label, error, hint, required, className, children }: FieldProps) {
  const id = useId();
  const messageId = `${id}-message`;
  const message = error ?? hint;

  return (
    <div className={cn("flex flex-col gap-1.5", className)}>
      <label htmlFor={id} className="text-xs font-semibold tracking-wide text-fg-secondary">
        {label}
        {required && (
          <span className="ml-0.5 text-danger" aria-hidden>
            *
          </span>
        )}
      </label>

      {cloneElement(children, {
        id,
        "aria-invalid": error ? true : undefined,
        "aria-describedby": message ? messageId : undefined,
      })}

      {message && (
        <p
          id={messageId}
          role={error ? "alert" : undefined}
          className={cn("text-xs", error ? "text-danger-text" : "text-fg-muted")}
        >
          {message}
        </p>
      )}
    </div>
  );
}
