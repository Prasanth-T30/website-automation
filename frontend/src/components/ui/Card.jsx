import { cn } from "@/lib/cn";
export function Card({ className, ...props }) {
  return (
    <div
      className={cn("rounded-lg border border-line-subtle bg-surface shadow-e1", className)}
      {...props}
    />
  );
}
export function CardHeader({ title, description, action, className }) {
  return (
    <div
      className={cn(
        "flex items-start justify-between gap-4 border-b border-line-subtle px-5 py-4",
        className,
      )}
    >
      <div className="min-w-0">
        <h2 className="font-display text-[19px] font-medium text-fg">{title}</h2>
        {description && <p className="mt-0.5 text-xs text-fg-muted">{description}</p>}
      </div>
      {action}
    </div>
  );
}
export function CardBody({ className, ...props }) {
  return <div className={cn("p-5", className)} {...props} />;
}
