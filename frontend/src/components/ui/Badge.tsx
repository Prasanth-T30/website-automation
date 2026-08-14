import { cva, type VariantProps } from "class-variance-authority";
import type { HTMLAttributes } from "react";

import { cn } from "@/lib/cn";

const badge = cva(
  "inline-flex items-center gap-1 rounded-sm px-2 py-0.5 text-xs font-semibold whitespace-nowrap",
  {
    variants: {
      tone: {
        neutral: "bg-subtle text-fg-secondary",
        brand: "bg-brand-subtle text-[var(--brand-text)]",
        success: "bg-success-subtle text-success-text",
        warn: "bg-warn-subtle text-warn-text",
        danger: "bg-danger-subtle text-danger-text",
      },
    },
    defaultVariants: { tone: "neutral" },
  },
);

export function Badge({
  className,
  tone,
  ...props
}: HTMLAttributes<HTMLSpanElement> & VariantProps<typeof badge>) {
  return <span className={cn(badge({ tone }), className)} {...props} />;
}
