import { CalendarCheck } from "lucide-react";
import { useMemo, useState } from "react";
import { toast } from "sonner";

import { MockBanner } from "@/components/MockBanner";
import { PageHeader } from "@/components/PageHeader";
import { Avatar } from "@/components/ui/Avatar";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/States";
import { cn } from "@/lib/cn";
import { shortDate } from "@/lib/format";
import {
  MOCK_ATTENDANCE,
  MOCK_BATCHES,
  MOCK_STUDENTS,
  type AttendanceStatus,
} from "@/mock/data";

const CYCLE: AttendanceStatus[] = ["present", "late", "absent"];
const LABEL: Record<AttendanceStatus, string> = { present: "P", late: "L", absent: "A" };
const STYLE: Record<AttendanceStatus, string> = {
  present: "bg-success-subtle text-success-text border-success/30",
  late: "bg-warn-subtle text-warn-text border-warn/30",
  absent: "bg-danger-subtle text-danger-text border-danger/30",
};

export default function Attendance() {
  const activeBatches = MOCK_BATCHES.filter((b) => b.status === "active");
  const [batchId, setBatchId] = useState(activeBatches[0]?.id ?? "");
  const [overrides, setOverrides] = useState<Record<string, AttendanceStatus>>({});

  const roster = useMemo(
    () => MOCK_STUDENTS.filter((s) => s.batch_id === batchId && s.status === "active"),
    [batchId],
  );

  const dates = useMemo(() => {
    const set = new Set(MOCK_ATTENDANCE.filter((a) => a.batch_id === batchId).map((a) => a.date));
    return [...set].sort();
  }, [batchId]);

  const statusFor = (studentId: string, date: string): AttendanceStatus => {
    const key = `${studentId}|${date}`;
    if (overrides[key]) return overrides[key];
    return (
      MOCK_ATTENDANCE.find((a) => a.student_id === studentId && a.date === date)?.status ??
      "present"
    );
  };

  const cycle = (studentId: string, date: string) => {
    const key = `${studentId}|${date}`;
    const current = statusFor(studentId, date);
    const next = CYCLE[(CYCLE.indexOf(current) + 1) % CYCLE.length]!;
    setOverrides((prev) => ({ ...prev, [key]: next }));
  };

  const markAllPresent = () => {
    const today = dates[dates.length - 1];
    if (!today) return;
    const next: Record<string, AttendanceStatus> = { ...overrides };
    for (const s of roster) next[`${s.id}|${today}`] = "present";
    setOverrides(next);
    toast.success(`Marked ${roster.length} students present for today.`);
  };

  return (
    <>
      <PageHeader
        title="Attendance"
        description="Click a cell to cycle Present → Late → Absent. Changes here are local only."
        action={<Button onClick={markAllPresent}>Mark today all present</Button>}
      />
      <MockBanner phase="Phase 3 — Core HRM: students, batches, attendance" />

      <div className="flex gap-1 overflow-x-auto px-6 pt-4">
        {activeBatches.map((b) => (
          <button
            key={b.id}
            onClick={() => setBatchId(b.id)}
            className={cn(
              "rounded-md px-3 py-1.5 text-xs font-semibold whitespace-nowrap transition-colors",
              batchId === b.id ? "bg-brand text-on-brand" : "text-fg-secondary hover:bg-subtle",
            )}
          >
            {b.code}
          </button>
        ))}
      </div>

      <div className="p-6 pt-4">
        <Card className="overflow-hidden">
          {roster.length === 0 ? (
            <EmptyState
              icon={<CalendarCheck className="size-6" />}
              title="No active students in this batch"
            />
          ) : (
            <div className="scroll-x">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-line-subtle bg-subtle/60 text-left">
                    <th className="sticky left-0 bg-subtle/60 px-4 py-2.5 text-xs font-bold tracking-wide text-fg-muted uppercase">
                      Student
                    </th>
                    {dates.map((d) => (
                      <th
                        key={d}
                        className="px-2 py-2.5 text-center text-xs font-bold tracking-wide text-fg-muted"
                      >
                        {shortDate(d).slice(0, 6)}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {roster.map((s) => (
                    <tr key={s.id} className="border-b border-line-subtle last:border-0">
                      <td className="sticky left-0 bg-surface px-4 py-2">
                        <div className="flex items-center gap-2">
                          <Avatar name={s.name} size="sm" />
                          <span className="text-sm font-medium text-fg">{s.name}</span>
                        </div>
                      </td>
                      {dates.map((d) => {
                        const status = statusFor(s.id, d);
                        return (
                          <td key={d} className="px-2 py-2 text-center">
                            <button
                              onClick={() => cycle(s.id, d)}
                              className={cn(
                                "inline-flex size-7 items-center justify-center rounded-full border text-xs font-bold transition-transform hover:scale-110",
                                STYLE[status],
                              )}
                              title={status}
                            >
                              {LABEL[status]}
                            </button>
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>
    </>
  );
}
