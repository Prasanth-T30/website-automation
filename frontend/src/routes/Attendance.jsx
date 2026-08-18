import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { subDays } from "date-fns";
import { CalendarCheck } from "lucide-react";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import { PageHeader } from "@/components/PageHeader";
import { Avatar } from "@/components/ui/Avatar";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/States";
import { attendanceApi } from "@/features/attendance/api";
import { batchesApi } from "@/features/batches/api";
import { studentsApi } from "@/features/students/api";
import { ApiError } from "@/lib/api";
import { cn } from "@/lib/cn";
import { shortDate } from "@/lib/format";
const CYCLE = ["present", "late", "absent"];
const LABEL = { present: "P", late: "L", absent: "A" };
const STYLE = {
  present: "bg-success-subtle text-success-text border-success/30",
  late: "bg-warn-subtle text-warn-text border-warn/30",
  absent: "bg-danger-subtle text-danger-text border-danger/30",
};
function isoDate(d) {
  return d.toISOString().slice(0, 10);
}
const DATES = Array.from({ length: 7 }, (_, i) => isoDate(subDays(new Date(), 6 - i)));
export default function Attendance() {
  const queryClient = useQueryClient();
  const [batchId, setBatchId] = useState(null);
  const batches = useQuery({
    queryKey: ["batches", { status: "active" }],
    queryFn: () => batchesApi.list({ status: "active" }),
  });
  const activeBatchId = batchId ?? batches.data?.[0]?.id ?? null;
  const roster = useQuery({
    queryKey: ["students", { batch_id: activeBatchId }],
    queryFn: () => studentsApi.list({ batch_id: activeBatchId }),
    enabled: !!activeBatchId,
  });
  const records = useQuery({
    queryKey: ["attendance", { batch_id: activeBatchId }],
    queryFn: () => attendanceApi.list({ batch_id: activeBatchId }),
    enabled: !!activeBatchId,
  });
  const statusMap = useMemo(() => {
    const map = new Map();
    for (const r of records.data ?? []) map.set(`${r.student_id}|${r.date}`, r.status);
    return map;
  }, [records.data]);
  const mark = useMutation({
    mutationFn: attendanceApi.mark,
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: ["attendance", { batch_id: activeBatchId }],
      });
    },
    onError: (err) =>
      toast.error(err instanceof ApiError ? err.detail : "Could not mark attendance."),
  });
  const cycle = (studentId, date) => {
    const current = statusMap.get(`${studentId}|${date}`);
    const next =
      current === undefined ? "present" : CYCLE[(CYCLE.indexOf(current) + 1) % CYCLE.length];
    mark.mutate({ student_id: studentId, batch_id: activeBatchId, date, status: next });
  };
  const markAllPresent = () => {
    if (!activeBatchId || !roster.data) return;
    const today = DATES[DATES.length - 1];
    for (const s of roster.data) {
      mark.mutate({ student_id: s.id, batch_id: activeBatchId, date: today, status: "present" });
    }
    toast.success(`Marking ${roster.data.length} students present for today.`);
  };
  const activeRoster = (roster.data ?? []).filter((s) => s.status === "active");
  return (
    <>
      <PageHeader
        title="Attendance"
        description="Click a cell to cycle Present → Late → Absent."
        action={
          <Button onClick={markAllPresent} disabled={!activeBatchId || !roster.data?.length}>
            Mark today all present
          </Button>
        }
      />

      {batches.isPending && <LoadingState label="Loading batches…" />}

      {batches.data && batches.data.length === 0 && (
        <div className="p-6">
          <Card>
            <EmptyState
              icon={<CalendarCheck className="size-6" />}
              title="No active batches"
              description="Attendance can only be marked for active batches."
            />
          </Card>
        </div>
      )}

      {batches.data && batches.data.length > 0 && (
        <>
          <div className="flex gap-1 overflow-x-auto px-6 pt-4">
            {batches.data.map((b) => (
              <button
                key={b.id}
                onClick={() => setBatchId(b.id)}
                className={cn(
                  "rounded-md px-3 py-1.5 text-xs font-semibold whitespace-nowrap transition-colors",
                  activeBatchId === b.id
                    ? "bg-brand text-on-brand"
                    : "text-fg-secondary hover:bg-subtle",
                )}
              >
                {b.code}
              </button>
            ))}
          </div>

          <div className="p-6 pt-4">
            <Card className="overflow-hidden">
              {roster.isPending && <LoadingState label="Loading roster…" />}

              {roster.isError && (
                <ErrorState
                  description={
                    roster.error instanceof ApiError
                      ? roster.error.detail
                      : "Could not load roster."
                  }
                  onRetry={() => roster.refetch()}
                />
              )}

              {roster.data && activeRoster.length === 0 && (
                <EmptyState
                  icon={<CalendarCheck className="size-6" />}
                  title="No active students in this batch"
                />
              )}

              {activeRoster.length > 0 && (
                <div className="scroll-x">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-line-subtle bg-subtle/60 text-left">
                        <th className="sticky left-0 bg-subtle/60 px-4 py-2.5 text-xs font-bold tracking-wide text-fg-muted uppercase">
                          Student
                        </th>
                        {DATES.map((d) => (
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
                      {activeRoster.map((s) => (
                        <tr key={s.id} className="border-b border-line-subtle last:border-0">
                          <td className="sticky left-0 bg-surface px-4 py-2">
                            <div className="flex items-center gap-2">
                              <Avatar name={s.name} size="sm" />
                              <span className="text-sm font-medium text-fg">{s.name}</span>
                            </div>
                          </td>
                          {DATES.map((d) => {
                            const marked = statusMap.get(`${s.id}|${d}`);
                            return (
                              <td key={d} className="px-2 py-2 text-center">
                                <button
                                  onClick={() => cycle(s.id, d)}
                                  className={cn(
                                    "inline-flex size-7 items-center justify-center rounded-full border text-xs font-bold transition-transform hover:scale-110",
                                    marked
                                      ? STYLE[marked]
                                      : "border-line-subtle text-fg-muted hover:border-line",
                                  )}
                                  title={marked ?? "Not marked"}
                                >
                                  {marked ? LABEL[marked] : "—"}
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
      )}
    </>
  );
}
