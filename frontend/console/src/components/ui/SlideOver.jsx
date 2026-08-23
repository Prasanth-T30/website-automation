import * as RadixDialog from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import { cn } from "@/lib/cn";
/**
 * Right-hand detail panel — the desktop app used modals for everything,
 * which loses table context. This keeps the underlying list visible and
 * scrollable behind it.
 */
export function SlideOver({ open, onOpenChange, title, description, children, className }) {
  return (
    <RadixDialog.Root open={open} onOpenChange={onOpenChange}>
      <RadixDialog.Portal>
        <RadixDialog.Overlay
          className={cn(
            "fixed inset-0 z-50 bg-brand-950/40 backdrop-blur-[2px] transition-opacity duration-200",
            "data-[state=closed]:opacity-0 data-[state=open]:opacity-100",
          )}
        />
        <RadixDialog.Content
          className={cn(
            "fixed top-0 right-0 z-50 flex h-dvh w-full max-w-lg flex-col border-l border-line-subtle bg-surface shadow-e2",
            "transition-transform duration-200 ease-out",
            "data-[state=closed]:translate-x-full data-[state=open]:translate-x-0",
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

          <div className="flex-1 overflow-y-auto">{children}</div>
        </RadixDialog.Content>
      </RadixDialog.Portal>
    </RadixDialog.Root>
  );
}
