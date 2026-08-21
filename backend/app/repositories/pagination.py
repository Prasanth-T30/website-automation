"""Cursor pagination for the Firestore-backed repositories.

Why cursors rather than offsets
-------------------------------
Firestore charges for every document a query reads, and `offset(n)` still
reads and bills the n documents it skips. Page 50 of an offset-paged list
costs fifty pages' worth of reads to return one. A cursor starts the scan at
the last document seen, so page 50 costs the same as page 1.

Why order by document id
------------------------
An equality filter combined with `order_by` on an ordinary field needs a
composite index for every filter/sort pair. Ordering by `__name__` — the
document id — needs none, and ids are unique, so the order is total and a
cursor can never straddle two documents with equal sort keys.

A caveat worth stating plainly
------------------------------
Several repositories apply a second filter in Python after the query returns,
because Firestore would need a composite index to express it. Pagination
happens at the Firestore level, *before* that filter runs, so a page can come
back holding fewer items than `limit` — even zero — while later pages still
have matches. Callers must therefore keep following `next_cursor` until it is
None rather than stopping at the first short page.
"""

from __future__ import annotations

from dataclasses import dataclass

from google.cloud.firestore import Query

# A single request should never be able to ask for the whole collection.
MAX_PAGE_SIZE = 500
DEFAULT_PAGE_SIZE = 50


@dataclass
class Page[T]:
    """One page of results, plus where to resume."""

    items: list[T]
    # The id to pass back as `cursor` for the next page. None means the scan
    # reached the end of the collection.
    next_cursor: str | None

    def __len__(self) -> int:
        return len(self.items)

    def __iter__(self):
        return iter(self.items)


def clamp_page_size(limit: int | None) -> int:
    if limit is None:
        return DEFAULT_PAGE_SIZE
    return max(1, min(int(limit), MAX_PAGE_SIZE))


def apply_cursor(query: Query, *, limit: int, cursor: str | None) -> Query:
    """Order by document id, resume after `cursor`, and cap the read.

    One extra document is fetched beyond `limit` so the caller can tell "this
    is the last page" from "there is more" without a second round trip.
    """
    query = query.order_by("__name__")
    if cursor:
        query = query.start_after({"__name__": cursor})
    return query.limit(limit + 1)


def split_overfetch(docs: list, limit: int) -> tuple[list, str | None]:
    """Trim the sentinel document and report the cursor it stood for."""
    if len(docs) <= limit:
        return docs, None
    kept = docs[:limit]
    return kept, kept[-1].id
