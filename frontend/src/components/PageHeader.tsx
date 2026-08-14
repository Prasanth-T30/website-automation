import type { ReactNode } from "react";

export function PageHeader({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-4 border-b border-line-subtle px-6 py-5">
      <div className="min-w-0">
        <h1 className="text-lg font-extrabold tracking-tight text-fg">{title}</h1>
        {description && <p className="mt-1 text-sm text-fg-muted">{description}</p>}
      </div>
      {action}
    </div>
  );
}
