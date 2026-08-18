import { ChevronLeft, ChevronRight } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { cn } from "@/lib/cn";

export const DEFAULT_PAGE_SIZE = 15;

/**
 * Client-side paging over an already-loaded array.
 *
 * The lists here are hundreds of rows, not millions, and every screen already
 * fetches the whole set to compute its own summary tiles. Slicing in the
 * browser keeps those totals correct and avoids a second round trip per page;
 * if a list ever outgrows that, this is the single place to swap in a
 * server-side cursor.
 *
 * @template T
 * @param {T[]} items
 * @param {number} [pageSize]
 * @returns {{ page: number, setPage: (n: number) => void, pageCount: number,
 *   pageItems: T[], total: number, from: number, to: number }}
 */
export function usePagination(items, pageSize = DEFAULT_PAGE_SIZE) {
  const [page, setPage] = useState(1);
  const total = items.length;
  const pageCount = Math.max(1, Math.ceil(total / pageSize));

  // Filtering can shrink the list under the current page — snap back rather
  // than stranding the user on an empty one.
  useEffect(() => {
    if (page > pageCount) setPage(1);
  }, [page, pageCount]);

  const safePage = Math.min(page, pageCount);
  const pageItems = useMemo(
    () => items.slice((safePage - 1) * pageSize, safePage * pageSize),
    [items, safePage, pageSize],
  );

  return {
    page: safePage,
    setPage,
    pageCount,
    pageItems,
    total,
    from: total === 0 ? 0 : (safePage - 1) * pageSize + 1,
    to: Math.min(safePage * pageSize, total),
  };
}

/** Page numbers to render, collapsing long runs to a single ellipsis. */
function pageWindow(page, pageCount) {
  if (pageCount <= 7) return Array.from({ length: pageCount }, (_, i) => i + 1);
  if (page <= 4) return [1, 2, 3, 4, 5, "…", pageCount];
  if (page >= pageCount - 3) {
    return [1, "…", pageCount - 4, pageCount - 3, pageCount - 2, pageCount - 1, pageCount];
  }
  return [1, "…", page - 1, page, page + 1, "…", pageCount];
}

const navButton =
  "flex size-8 items-center justify-center rounded-md border border-line bg-surface " +
  "text-fg-secondary transition-colors hover:bg-subtle hover:text-fg " +
  "disabled:pointer-events-none disabled:opacity-40";

/**
 * Paging footer. Renders nothing when everything fits on one page, so short
 * lists stay uncluttered.
 */
export function Pagination({ page, pageCount, setPage, from, to, total, label = "rows" }) {
  if (pageCount <= 1) return null;

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 border-t border-line-subtle px-4 py-3">
      <p className="text-xs text-fg-muted">
        Showing <span className="font-semibold text-fg-secondary">{from}</span>–
        <span className="font-semibold text-fg-secondary">{to}</span> of{" "}
        <span className="font-semibold text-fg-secondary">{total}</span> {label}
      </p>

      <nav className="flex items-center gap-1" aria-label="Pagination">
        <button
          type="button"
          className={navButton}
          onClick={() => setPage(page - 1)}
          disabled={page === 1}
          aria-label="Previous page"
        >
          <ChevronLeft className="size-4" aria-hidden />
        </button>

        {pageWindow(page, pageCount).map((n, i) =>
          n === "…" ? (
            <span key={`gap-${i}`} className="px-1 text-xs text-fg-muted">
              …
            </span>
          ) : (
            <button
              key={n}
              type="button"
              onClick={() => setPage(n)}
              aria-current={n === page ? "page" : undefined}
              className={cn(
                "h-8 min-w-8 rounded-md px-2 text-xs font-semibold transition-colors",
                n === page
                  ? "bg-brand text-on-brand"
                  : "border border-line bg-surface text-fg-secondary hover:bg-subtle hover:text-fg",
              )}
            >
              {n}
            </button>
          ),
        )}

        <button
          type="button"
          className={navButton}
          onClick={() => setPage(page + 1)}
          disabled={page === pageCount}
          aria-label="Next page"
        >
          <ChevronRight className="size-4" aria-hidden />
        </button>
      </nav>
    </div>
  );
}
