import { AlertTriangle, Loader2 } from "lucide-react";
import type { ReactNode } from "react";

import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/cn";

/**
 * Shared loading / empty / error presentations. The desktop app improvised
 * these per screen, which is why they read inconsistently; here they are one
 * component so every list behaves the same.
 */

export function LoadingState({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-2 py-12 text-sm text-fg-muted">
      <Loader2 className="size-4 animate-spin" aria-hidden />
      <span role="status">{label}</span>
    </div>
  );
}

export function EmptyState({
  icon,
  title,
  description,
  action,
  className,
}: {
  icon?: ReactNode;
  title: string;
  description?: string;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex flex-col items-center gap-2 px-6 py-14 text-center", className)}>
      {icon && <div className="mb-1 text-fg-muted">{icon}</div>}
      <p className="text-sm font-semibold text-fg">{title}</p>
      {description && <p className="max-w-sm text-xs text-fg-muted">{description}</p>}
      {action && <div className="mt-3">{action}</div>}
    </div>
  );
}

export function ErrorState({
  title = "Something went wrong",
  description,
  onRetry,
}: {
  title?: string;
  description?: string;
  onRetry?: () => void;
}) {
  return (
    <div className="flex flex-col items-center gap-2 px-6 py-14 text-center">
      <AlertTriangle className="size-6 text-danger" aria-hidden />
      <p className="text-sm font-semibold text-fg">{title}</p>
      {description && <p className="max-w-sm text-xs text-fg-muted">{description}</p>}
      {onRetry && (
        <Button variant="secondary" size="sm" className="mt-3" onClick={onRetry}>
          Try again
        </Button>
      )}
    </div>
  );
}
