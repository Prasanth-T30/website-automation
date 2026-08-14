import { FlaskConical } from "lucide-react";

/**
 * Marks a screen as a visual preview: realistic data, but nothing here reads
 * from or writes to the backend. Every module carrying this banner has a
 * corresponding real build phase still ahead of it.
 */
export function MockBanner({ phase }: { phase: string }) {
  return (
    <div className="mx-6 mt-4 flex items-center gap-2.5 rounded-md border border-accent-300/40 bg-accent-50 px-3.5 py-2.5 text-xs text-accent-800 dark:border-accent-700/40 dark:bg-accent-900/20 dark:text-accent-300">
      <FlaskConical className="size-4 shrink-0" aria-hidden />
      <span>
        <strong className="font-semibold">Preview</strong> — sample data for layout review only.
        Not yet connected to the backend ({phase}).
      </span>
    </div>
  );
}
