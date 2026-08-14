import {
  DndContext,
  DragOverlay,
  PointerSensor,
  useDroppable,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { useMemo, useState } from "react";
import { toast } from "sonner";

import { MockBanner } from "@/components/MockBanner";
import { PageHeader } from "@/components/PageHeader";
import { Avatar } from "@/components/ui/Avatar";
import { Badge } from "@/components/ui/Badge";
import { cn } from "@/lib/cn";
import {
  MOCK_APPLICATIONS,
  MOCK_STUDENTS,
  PIPELINE_STAGES,
  hrName,
  type MockApplication,
  type PipelineStage,
} from "@/mock/data";

type ColumnKey = "pool" | PipelineStage;

interface Card {
  id: string;
  title: string;
  subtitle: string;
  ownerId: string | null;
  column: ColumnKey;
}

function buildInitialCards(): Card[] {
  const pool: Card[] = MOCK_APPLICATIONS.filter((a) => a.status === "new").map(
    (a: MockApplication) => ({
      id: a.id,
      title: a.full_name,
      subtitle: a.domain_interest,
      ownerId: null,
      column: "pool",
    }),
  );
  const staged: Card[] = MOCK_STUDENTS.filter((s) => s.status !== "dropped").map((s) => ({
    id: s.id,
    title: s.name,
    subtitle: s.domain,
    ownerId: s.owner_id,
    column: s.pipeline_stage,
  }));
  return [...pool, ...staged];
}

const COLUMNS: { key: ColumnKey; label: string; hint: string }[] = [
  { key: "pool", label: "Unassigned Pool", hint: "New applications — claim to take ownership" },
  ...PIPELINE_STAGES.map((s) => ({ key: s.key as ColumnKey, label: s.label, hint: "" })),
];

function BoardCard({ card, dragging }: { card: Card; dragging?: boolean }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: card.id,
  });

  return (
    <div
      ref={setNodeRef}
      {...attributes}
      {...listeners}
      style={{ transform: CSS.Translate.toString(transform), transition }}
      className={cn(
        "cursor-grab touch-none rounded-md border border-line-subtle bg-surface p-3 shadow-e1 active:cursor-grabbing",
        (isDragging || dragging) && "opacity-40",
      )}
    >
      <p className="text-sm font-semibold text-fg">{card.title}</p>
      <p className="mt-0.5 text-xs text-fg-muted">{card.subtitle}</p>
      <div className="mt-2.5 flex items-center justify-between">
        {card.ownerId ? (
          <div className="flex items-center gap-1.5">
            <Avatar name={hrName(card.ownerId)} size="sm" />
            <span className="text-xs text-fg-secondary">{hrName(card.ownerId)}</span>
          </div>
        ) : (
          <Badge tone="warn">Unclaimed</Badge>
        )}
      </div>
    </div>
  );
}

function Column({
  col,
  cards,
}: {
  col: { key: ColumnKey; label: string; hint: string };
  cards: Card[];
}) {
  const { setNodeRef, isOver } = useDroppable({ id: col.key });

  return (
    <div className="flex w-72 shrink-0 flex-col rounded-lg bg-subtle/60">
      <div className="flex items-center justify-between px-3 py-2.5">
        <div>
          <p className="text-xs font-bold tracking-wide text-fg uppercase">{col.label}</p>
          {col.hint && <p className="mt-0.5 max-w-[220px] text-[11px] text-fg-muted">{col.hint}</p>}
        </div>
        <Badge tone="neutral">{cards.length}</Badge>
      </div>
      <div
        ref={setNodeRef}
        className={cn(
          "flex min-h-[120px] flex-1 flex-col gap-2 p-2 pt-0 transition-colors",
          isOver && "bg-brand-subtle/50",
        )}
      >
        {cards.map((c) => (
          <BoardCard key={c.id} card={c} />
        ))}
        {cards.length === 0 && (
          <p className="px-2 py-6 text-center text-xs text-fg-muted">Nothing here</p>
        )}
      </div>
    </div>
  );
}

export default function Pipeline() {
  const [cards, setCards] = useState<Card[]>(buildInitialCards);
  const [activeId, setActiveId] = useState<string | null>(null);
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 6 } }));

  const byColumn = useMemo(() => {
    const map = new Map<ColumnKey, Card[]>(COLUMNS.map((c) => [c.key, []]));
    for (const card of cards) map.get(card.column)?.push(card);
    return map;
  }, [cards]);

  const activeCard = cards.find((c) => c.id === activeId) ?? null;

  function handleDragStart(e: DragStartEvent) {
    setActiveId(String(e.active.id));
  }

  function handleDragEnd(e: DragEndEvent) {
    setActiveId(null);
    const { active, over } = e;
    if (!over) return;

    const targetColumn = COLUMNS.find((c) => c.key === over.id)?.key;
    if (!targetColumn) return;

    setCards((prev) =>
      prev.map((c) => {
        if (c.id !== active.id) return c;
        if (c.column === "pool" && targetColumn !== "pool") {
          toast.success(`${c.title} claimed under your name.`);
          return { ...c, column: targetColumn, ownerId: "hr-1" };
        }
        return { ...c, column: targetColumn };
      }),
    );
  }

  return (
    <>
      <PageHeader
        title="Pipeline"
        description="Drag a card out of the pool to claim it. Everything here resets on refresh — this is a layout preview."
      />
      <MockBanner phase="Phase 2 — Public intake, shared pool and claim" />

      <div className="scroll-x p-6">
        <DndContext
          sensors={sensors}
          onDragStart={handleDragStart}
          onDragEnd={handleDragEnd}
        >
          <div className="flex gap-4 pb-2">
            {COLUMNS.map((col) => (
              <Column key={col.key} col={col} cards={byColumn.get(col.key) ?? []} />
            ))}
          </div>
          <DragOverlay>
            {activeCard ? <BoardCard card={activeCard} dragging /> : null}
          </DragOverlay>
        </DndContext>
      </div>

    </>
  );
}
