export function PageHeader({ title, description, action }) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-4 px-6 py-6">
      <div className="min-w-0">
        <h1 className="font-display text-[34px] leading-tight font-normal tracking-tight text-fg">
          {title}
        </h1>
        {description && <p className="mt-1.5 text-sm text-fg-muted">{description}</p>}
      </div>
      {action}
    </div>
  );
}
