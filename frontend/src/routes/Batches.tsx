import { Layers, Users } from "lucide-react";
import { useState } from "react";

import { MockBanner } from "@/components/MockBanner";
import { PageHeader } from "@/components/PageHeader";
import { Avatar } from "@/components/ui/Avatar";
import { Badge } from "@/components/ui/Badge";
import { Card, CardBody } from "@/components/ui/Card";
import { SlideOver } from "@/components/ui/SlideOver";
import { shortDate } from "@/lib/format";
import { MOCK_BATCHES, MOCK_STUDENTS, hrName, type BatchStatus, type MockBatch } from "@/mock/data";

const TONE: Record<BatchStatus, "brand" | "success" | "warn"> = {
  active: "brand",
  completed: "success",
  upcoming: "warn",
};

export default function Batches() {
  const [selected, setSelected] = useState<MockBatch | null>(null);

  return (
    <>
      <PageHeader
        title="Batches"
        description={`${MOCK_BATCHES.length} batches — ${MOCK_BATCHES.filter((b) => b.status === "active").length} currently active.`}
      />
      <MockBanner phase="Phase 3 — Core HRM: students, batches, attendance" />

      <div className="grid grid-cols-1 gap-4 p-6 sm:grid-cols-2 lg:grid-cols-3">
        {MOCK_BATCHES.map((b) => (
          <Card
            key={b.id}
            className="cursor-pointer transition-shadow hover:shadow-e2"
            onClick={() => setSelected(b)}
          >
            <CardBody className="flex flex-col gap-3">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <p className="text-sm font-bold text-fg">{b.code}</p>
                  <p className="text-xs text-fg-muted">{b.domain}</p>
                </div>
                <Badge tone={TONE[b.status]} className="capitalize">{b.status}</Badge>
              </div>

              <div className="flex items-center gap-1.5 text-xs text-fg-secondary">
                <Users className="size-3.5" />
                {b.student_count} / {b.capacity} enrolled
              </div>

              <div className="h-1.5 overflow-hidden rounded-full bg-subtle">
                <div
                  className="h-full rounded-full bg-brand"
                  style={{ width: `${Math.min((b.student_count / b.capacity) * 100, 100)}%` }}
                />
              </div>

              <p className="text-xs text-fg-muted">
                {shortDate(b.start_date)} → {shortDate(b.end_date)}
                {b.days_left !== null && b.status === "active" && (
                  <span className={b.days_left <= 7 ? "ml-1.5 font-semibold text-danger-text" : "ml-1.5"}>
                    · {b.days_left}d left
                  </span>
                )}
              </p>
            </CardBody>
          </Card>
        ))}
      </div>

      <SlideOver
        open={selected !== null}
        onOpenChange={(o) => !o && setSelected(null)}
        title={selected?.code ?? ""}
        description={selected?.domain}
      >
        {selected && <BatchRoster batch={selected} />}
      </SlideOver>
    </>
  );
}

function BatchRoster({ batch }: { batch: MockBatch }) {
  const roster = MOCK_STUDENTS.filter((s) => s.batch_id === batch.id);

  return (
    <div className="flex flex-col gap-5 p-5">
      <Card>
        <CardBody className="grid grid-cols-2 gap-4">
          {[
            ["Status", batch.status],
            ["Capacity", `${batch.student_count} / ${batch.capacity}`],
            ["Starts", shortDate(batch.start_date)],
            ["Ends", shortDate(batch.end_date)],
          ].map(([label, value]) => (
            <div key={label}>
              <p className="text-[10px] font-bold tracking-wide text-fg-muted uppercase">{label}</p>
              <p className="mt-0.5 text-sm text-fg capitalize">{value}</p>
            </div>
          ))}
        </CardBody>
      </Card>

      <div>
        <div className="mb-2 flex items-center gap-2">
          <Layers className="size-4 text-fg-muted" />
          <h3 className="text-xs font-bold tracking-wide text-fg-muted uppercase">
            Roster ({roster.length})
          </h3>
        </div>
        <ul className="divide-y divide-line-subtle rounded-md border border-line-subtle">
          {roster.map((s) => (
            <li key={s.id} className="flex items-center gap-2.5 px-3 py-2.5">
              <Avatar name={s.name} size="sm" />
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-fg">{s.name}</p>
                <p className="text-xs text-fg-muted">{s.student_id} · {hrName(s.owner_id)}</p>
              </div>
              <Badge tone={s.payment_status === "paid" ? "success" : s.payment_status === "overdue" ? "danger" : "warn"}>
                {s.payment_status}
              </Badge>
            </li>
          ))}
          {roster.length === 0 && (
            <li className="px-3 py-6 text-center text-xs text-fg-muted">No students yet.</li>
          )}
        </ul>
      </div>
    </div>
  );
}
