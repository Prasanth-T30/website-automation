import { forwardRef } from "react";
import { cn } from "@/lib/cn";
export const Input = forwardRef(function Input({ className, ...props }, ref) {
  return (
    <input
      ref={ref}
      className={cn(
        "h-10 w-full rounded-md border border-line bg-surface px-3 text-sm text-fg",
        "placeholder:text-fg-muted",
        "transition-colors focus:border-brand",
        "disabled:cursor-not-allowed disabled:bg-subtle disabled:opacity-70",
        "aria-[invalid=true]:border-danger",
        className,
      )}
      {...props}
    />
  );
});
