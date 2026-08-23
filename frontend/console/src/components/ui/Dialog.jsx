import * as RadixDialog from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import { cn } from "@/lib/cn";
/** Radix handles focus trapping, escape, scroll lock and the ARIA wiring. */
export function Dialog({ open, onOpenChange, title, description, children, footer, className }) {
  return (
    <RadixDialog.Root open={open} onOpenChange={onOpenChange}>
      <RadixDialog.Portal>
        <RadixDialog.Overlay className="fixed inset-0 z-50 bg-brand-950/50 backdrop-blur-[2px]" />
        <RadixDialog.Content
          className={cn(
            "fixed top-1/2 left-1/2 z-50 w-[calc(100vw-2rem)] max-w-lg -translate-x-1/2 -translate-y-1/2",
            "max-h-[calc(100dvh-4rem)] overflow-y-auto rounded-lg border border-line-subtle bg-surface shadow-e2",
            className,
          )}
        >
          <div className="flex items-start justify-between gap-4 border-b border-line-subtle px-5 py-4">
            <div className="min-w-0">
              <RadixDialog.Title className="text-sm font-bold text-fg">{title}</RadixDialog.Title>
              {description && (
                <RadixDialog.Description className="mt-0.5 text-xs text-fg-muted">
                  {description}
                </RadixDialog.Description>
              )}
            </div>
            <RadixDialog.Close
              className="rounded-sm p-1 text-fg-muted transition-colors hover:bg-subtle hover:text-fg"
              aria-label="Close"
            >
              <X className="size-4" />
            </RadixDialog.Close>
          </div>

          <div className="p-5">{children}</div>

          {/* Pinned to the bottom of the scroll area. A dialog holding a tall
              preview would otherwise push its own actions out of view, and an
              embedded PDF swallows the scroll wheel — so the reader sees a
              document with no apparent way to act on it. */}
          {footer && (
            <div className="sticky bottom-0 flex justify-end gap-2 border-t border-line-subtle bg-surface px-5 py-3">
              {footer}
            </div>
          )}
        </RadixDialog.Content>
      </RadixDialog.Portal>
    </RadixDialog.Root>
  );
}
