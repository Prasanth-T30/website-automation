import { GraduationCap, Search } from "lucide-react";
import { useMemo, useState } from "react";

import { MockBanner } from "@/components/MockBanner";
import { PageHeader } from "@/components/PageHeader";
import { Avatar } from "@/components/ui/Avatar";
import { Badge } from "@/components/ui/Badge";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { SlideOver } from "@/components/ui/SlideOver";
import { EmptyState } from "@/components/ui/States";
import { money, shortDate } from "@/lib/format";
import {
  MOCK_ATTENDANCE,
  MOCK_STUDENTS,
  MOCK_TRANSACTIONS,
  batchCode,
  hrName,
  type MockStudent,
  type PaymentStatus,
  type StudentStatus,
} from "@/mock/data";

const PAY_TONE: Record<PaymentStatus, "success" | "warn" | "danger"> = {
  paid: "success",
  pending: "warn",
  overdue: "danger",
};

const STATUS_TONE: Record<StudentStatus, "brand" | "success" | "neutral"> = {
  active: "brand",
  completed: "success",
  dropped: "neutral",
};

export default function Students() {
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<StudentStatus | "all">("all");
  const [selected, setSelected] = useState<MockStudent | null>(null);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return MOCK_STUDENTS.filter((s) => {
      if (statusFilter !== "all" && s.status !== statusFilter) return false;
      if (!q) return true;
      return (
        s.name.toLowerCase().includes(q) ||
        s.student_id.toLowerCase().includes(q) ||
        s.college_name.toLowerCase().includes(q) ||
        s.email.toLowerCase().includes(q)
      );
    });
  }, [query, statusFilter]);

  return (
    <>
      <PageHeader
        title="Students"
        description={`${MOCK_STUDENTS.length} students across every batch and the unassigned pool.`}
      />
      <MockBanner phase="Phase 3 — Core HRM: students, batches, attendance" />

      <div className="flex flex-wrap items-center gap-3 px-6 pt-4">
        <div className="relative w-full max-w-xs">
          <Search className="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-fg-muted" />
          <Input
            className="pl-9"
            placeholder="Search name, ID, college…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
        <div className="flex gap-1">
          {(["all", "active", "completed", "dropped"] as const).map((s) => (
            <button
              key={s}
              onClick={() => setStatusFilter(s)}
              className={`rounded-md px-3 py-1.5 text-xs font-semibold capitalize transition-colors ${
                statusFilter === s ? "bg-brand text-on-brand" : "text-fg-secondary hover:bg-subtle"
              }`}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      <div className="p-6 pt-4">
        <Card className="overflow-hidden">
          {filtered.length === 0 ? (
            <EmptyState
              icon={<GraduationCap className="size-6" />}
              title="No students found"
              description="Try a different search or filter."
            />
          ) : (
            <div className="scroll-x">
              <table className="w-full min-w-[900px] text-sm">
                <thead>
                  <tr className="border-b border-line-subtle bg-subtle/60 text-left">
                    {["Student", "College", "Batch", "Owner", "Balance", "Status", ""].map((h) => (
                      <th
                        key={h}
                        className="px-4 py-2.5 text-xs font-bold tracking-wide text-fg-muted uppercase"
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((s) => {
                    const balance = s.total_fees - s.fees_paid;
                    return (
                      <tr
                        key={s.id}
                        onClick={() => setSelected(s)}
                        className="cursor-pointer border-b border-line-subtle last:border-0 hover:bg-subtle/60"
                      >
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-2.5">
                            <Avatar name={s.name} size="sm" />
                            <div>
                              <p className="font-medium text-fg">{s.name}</p>
                              <p className="text-xs text-fg-muted">{s.student_id} · {s.domain}</p>
                            </div>
                          </div>
                        </td>
                        <td className="px-4 py-3 text-fg-secondary">{s.college_name}</td>
                        <td className="px-4 py-3">
                          {s.batch_id ? (
                            <Badge tone="neutral">{batchCode(s.batch_id)}</Badge>
                          ) : (
                            <span className="text-xs text-fg-muted">Unassigned</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-xs text-fg-secondary">{hrName(s.owner_id)}</td>
                        <td className="px-4 py-3">
                          <Badge tone={PAY_TONE[s.payment_status]}>
                            {balance > 0 ? money(balance) : "Paid in full"}
                          </Badge>
                        </td>
                        <td className="px-4 py-3">
                          <Badge tone={STATUS_TONE[s.status]} className="capitalize">
                            {s.status}
                          </Badge>
                        </td>
                        <td />
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>

      <SlideOver
        open={selected !== null}
        onOpenChange={(o) => !o && setSelected(null)}
        title={selected?.name ?? ""}
        description={selected ? `${selected.student_id} · ${selected.domain}` : undefined}
      >
        {selected && <StudentDetail student={selected} />}
      </SlideOver>
    </>
  );
}

function StudentDetail({ student }: { student: MockStudent }) {
  const balance = student.total_fees - student.fees_paid;
  const transactions = MOCK_TRANSACTIONS.filter((t) => t.student_id === student.id);
  const attendance = MOCK_ATTENDANCE.filter((a) => a.student_id === student.id);
  const presentPct = attendance.length
    ? Math.round((attendance.filter((a) => a.status === "present").length / attendance.length) * 100)
    : null;

  return (
    <div className="flex flex-col gap-5 p-5">
      <div className="flex items-center gap-3">
        <Avatar name={student.name} size="lg" />
        <div>
          <p className="text-sm font-bold text-fg">{student.name}</p>
          <p className="text-xs text-fg-muted">{student.college_name}</p>
        </div>
      </div>

      <Card>
        <CardBody className="grid grid-cols-2 gap-4 !p-4">
          {[
            ["Email", student.email],
            ["Phone", student.phone],
            ["City", student.city],
            ["Owner", hrName(student.owner_id)],
            ["Batch", student.batch_id ? batchCode(student.batch_id) : "Unassigned"],
            ["Enrolled", shortDate(student.created_at)],
          ].map(([label, value]) => (
            <div key={label}>
              <p className="text-[10px] font-bold tracking-wide text-fg-muted uppercase">{label}</p>
              <p className="mt-0.5 text-sm text-fg">{value}</p>
            </div>
          ))}
        </CardBody>
      </Card>

      <Card>
        <CardHeader
          title="Payments"
          description={balance > 0 ? `${money(balance)} outstanding` : "Paid in full"}
        />
        <CardBody className="!p-0">
          {transactions.length === 0 ? (
            <p className="p-4 text-xs text-fg-muted">No payments recorded yet.</p>
          ) : (
            <ul className="divide-y divide-line-subtle">
              {transactions.map((t) => (
                <li key={t.id} className="flex items-center justify-between px-4 py-2.5 text-sm">
                  <div>
                    <p className="font-medium text-fg">{money(t.amount)}</p>
                    <p className="text-xs text-fg-muted">{t.receipt_number} · {shortDate(t.paid_at)}</p>
                  </div>
                  <Badge tone="neutral" className="uppercase">{t.mode}</Badge>
                </li>
              ))}
            </ul>
          )}
        </CardBody>
      </Card>

      {presentPct !== null && (
        <Card>
          <CardHeader title="Attendance" description="Last 7 sessions" />
          <CardBody className="!p-4">
            <div className="flex items-center gap-3">
              <div className="h-2 flex-1 overflow-hidden rounded-full bg-subtle">
                <div
                  className="h-full rounded-full bg-success"
                  style={{ width: `${presentPct}%` }}
                />
              </div>
              <span className="text-sm font-bold text-fg">{presentPct}%</span>
            </div>
          </CardBody>
        </Card>
      )}
    </div>
  );
}
