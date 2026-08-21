import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  Banknote,
  CheckCircle2,
  Clock,
  Download,
  FileSpreadsheet,
  FileText,
  Pencil,
  Plus,
  Search,
} from "lucide-react";
import { useMemo, useState } from "react";
import { PageHeader } from "@/components/PageHeader";
import { Avatar } from "@/components/ui/Avatar";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardBody } from "@/components/ui/Card";
import { Dialog } from "@/components/ui/Dialog";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Pagination, usePagination } from "@/components/ui/Pagination";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/States";
import { useAuth } from "@/features/auth/AuthProvider";
import { batchesApi } from "@/features/batches/api";
import { paymentsApi } from "@/features/payments/api";
import { studentsApi } from "@/features/students/api";
import { isOverdue } from "@/features/students/overdue";
import { usersApi } from "@/features/users/api";
import { ApiError } from "@/lib/api";
import { toast } from "sonner";
import { money, shortDate } from "@/lib/format";
const METHOD_TONE = {
  cash: "neutral",
  upi: "brand",
  bank_transfer: "success",
  card: "warn",
  other: "neutral",
};

// Cash and UPI are the only methods the institute actually collects through,
// so the filter offers just those two. Older records may still carry another
// method — those stay visible under "All methods" rather than disappearing.
const PAYMENT_METHOD_FILTERS = [
  { value: "cash", label: "Cash" },
  { value: "upi", label: "UPI" },
];

const filterSelectClass =
  "h-10 max-w-[16rem] rounded-md border border-line bg-surface px-2.5 text-xs font-semibold " +
  "text-fg-secondary outline-none transition-colors focus:border-brand";
function StatTile({ icon: Icon, label, value, tone }) {
  return (
    <Card>
      <CardBody className="flex items-center gap-3">
        <div className={`flex size-10 items-center justify-center rounded-md ${tone}`}>
          <Icon className="size-5" />
        </div>
        <div>
          <p className="text-xs font-semibold text-fg-muted">{label}</p>
          <p className="text-lg font-extrabold text-fg">{value}</p>
        </div>
      </CardBody>
    </Card>
  );
}
export default function Payments() {
  const { user, isAdmin } = useAuth();
  const [collegeFilter, setCollegeFilter] = useState("all");
  const [methodFilter, setMethodFilter] = useState("all");
  const [feeStatusFilter, setFeeStatusFilter] = useState("all");
  const [recordFor, setRecordFor] = useState(null);
  const [editFeeFor, setEditFeeFor] = useState(null);
  const queryClient = useQueryClient();
  const [receiptQuery, setReceiptQuery] = useState("");
  // Cross-HR revenue comparison is admin-only (the leaderboard lives on
  // /admin/hr-performance) — an HR's own ledger and stats only cover
  // students/transactions attributed to them, even though both list
  // endpoints stay open reads at the API level (same as Students).
  const transactions = useQuery({
    queryKey: ["payments", { mine: !isAdmin }],
    queryFn: () => paymentsApi.list(isAdmin ? undefined : { mine: true }),
  });
  const students = useQuery({ queryKey: ["students"], queryFn: () => studentsApi.list() });
  const batches = useQuery({ queryKey: ["batches"], queryFn: () => batchesApi.list() });
  // Admin-only: turns owner ids into names for the "Collected by" column.
  // An HR would get a 403 here, and has no use for it — every row is theirs.
  const staff = useQuery({
    queryKey: ["users"],
    queryFn: usersApi.list,
    enabled: isAdmin,
  });
  const staffName = (id) =>
    (staff.data ?? []).find((u) => u.id === id)?.full_name ?? "—";
  const studentById = useMemo(
    () => new Map((students.data ?? []).map((s) => [s.id, s])),
    [students.data],
  );
  const studentName = (id) => studentById.get(id)?.name ?? id;
  /** What a student still owes. Negative balances are clamped: over-payment
   *  is settled, not credit. */
  const balanceOf = (s) => (s ? Math.max(0, s.total_fees - s.fees_paid) : 0);
  /** Recording and fee edits belong to whoever claimed the student. The API
   *  enforces this too (403); this only decides whether to offer the control
   *  rather than let someone click into a refusal. */
  const canEdit = (s) => Boolean(s) && (isAdmin || s.owner_id === user?.id);

  // A transaction carries no college of its own — it inherits the one on the
  // student it belongs to, which is what "filter the finance page by college"
  // has to mean.
  const colleges = useMemo(() => {
    const seen = new Set();
    for (const t of transactions.data ?? []) {
      const college = studentById.get(t.student_id)?.college;
      if (college) seen.add(college);
    }
    return [...seen].sort((a, b) => a.localeCompare(b));
  }, [transactions.data, studentById]);

  const visibleTransactions = useMemo(() => {
    return (transactions.data ?? []).filter((t) => {
      if (methodFilter !== "all" && (t.method ?? "other") !== methodFilter) return false;
      if (feeStatusFilter !== "all") {
        // Fee status belongs to the student: a payment counts as "fully paid"
        // when the student it belongs to owes nothing further.
        const owed = balanceOf(studentById.get(t.student_id));
        if (feeStatusFilter === "paid" ? owed > 0 : owed <= 0) return false;
      }
      if (collegeFilter !== "all" && studentById.get(t.student_id)?.college !== collegeFilter) {
        return false;
      }
      if (!receiptQuery.trim()) return true;
      const q = receiptQuery.trim().toLowerCase();
      return (
        t.receipt_number.toLowerCase().includes(q) ||
        (studentById.get(t.student_id)?.name ?? "").toLowerCase().includes(q)
      );
    });
  }, [transactions.data, studentById, methodFilter, collegeFilter, receiptQuery, feeStatusFilter]);

  const paging = usePagination(visibleTransactions);

  const refreshMoney = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["payments"] }),
      queryClient.invalidateQueries({ queryKey: ["students"] }),
      queryClient.invalidateQueries({ queryKey: ["admin", "hr-performance"] }),
    ]);
  };

  // Mirrors the filters above so a download matches the table on screen.
  // `mine` tracks the same admin/HR scoping the list query already uses.
  const exportFilters = {
    mine: !isAdmin,
    method: methodFilter,
    college: collegeFilter,
    q: receiptQuery,
    fee_status: feeStatusFilter,
  };

  const summary = useMemo(() => {
    const rows = (students.data ?? []).filter((s) => isAdmin || s.owner_id === user?.id);
    const batchesById = new Map((batches.data ?? []).map((b) => [b.id, b]));
    const unpaid = rows.filter((s) => s.total_fees - s.fees_paid > 0);
    const overdue = unpaid.filter((s) => isOverdue(s, batchesById));
    const pending = unpaid.filter((s) => !isOverdue(s, batchesById));
    return {
      totalRevenue: (transactions.data ?? []).reduce((sum, t) => sum + t.amount, 0),
      pendingAmount: pending.reduce((sum, s) => sum + (s.total_fees - s.fees_paid), 0),
      overdueAmount: overdue.reduce((sum, s) => sum + (s.total_fees - s.fees_paid), 0),
      paidCount: rows.filter((s) => s.total_fees - s.fees_paid <= 0).length,
    };
  }, [transactions.data, students.data, batches.data, isAdmin, user?.id]);
  return (
    <>
      <PageHeader
        title="Payments"
        description="Every recorded transaction, newest first. Record a payment or adjust a fee straight from the row."
        action={
          <div className="flex items-center gap-2">
            <Button onClick={() => setRecordFor({})}>
              <Plus className="size-4" aria-hidden /> Record payment
            </Button>
            {/* Plain links, not fetches: the browser handles the download and
                the session cookie rides along automatically. */}
            <a
              href={paymentsApi.exportUrl("xlsx", exportFilters)}
              className="inline-flex h-10 items-center gap-2 rounded-md border border-line bg-surface px-4 text-sm font-semibold text-fg transition-colors hover:bg-subtle"
            >
              <FileSpreadsheet className="size-4" aria-hidden /> Excel
            </a>
            <a
              href={paymentsApi.exportUrl("pdf", exportFilters)}
              className="inline-flex h-10 items-center gap-2 rounded-md border border-line bg-surface px-4 text-sm font-semibold text-fg transition-colors hover:bg-subtle"
            >
              <FileText className="size-4" aria-hidden /> PDF
            </a>
          </div>
        }
      />

      <div className="grid grid-cols-1 gap-4 p-6 sm:grid-cols-2 lg:grid-cols-4">
        <StatTile
          icon={Banknote}
          label="Total Revenue"
          value={money(summary.totalRevenue)}
          tone="bg-success-subtle text-success"
        />
        <StatTile
          icon={Clock}
          label="Pending"
          value={money(summary.pendingAmount)}
          tone="bg-warn-subtle text-warn"
        />
        <StatTile
          icon={AlertTriangle}
          label="Overdue"
          value={money(summary.overdueAmount)}
          tone="bg-danger-subtle text-danger"
        />
        <StatTile
          icon={CheckCircle2}
          label="Fully Paid"
          value={`${summary.paidCount} students`}
          tone="bg-brand-subtle text-brand"
        />
      </div>

      <div className="flex flex-wrap items-center gap-3 px-6">
        <div className="relative w-full max-w-xs">
          <Search className="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-fg-muted" />
          <Input
            className="pl-9"
            placeholder="Search receipt or student…"
            value={receiptQuery}
            onChange={(e) => setReceiptQuery(e.target.value)}
          />
        </div>

        <select
          value={collegeFilter}
          onChange={(e) => setCollegeFilter(e.target.value)}
          aria-label="Filter by college"
          className={filterSelectClass}
        >
          <option value="all">All colleges</option>
          {colleges.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>

        <select
          value={feeStatusFilter}
          onChange={(e) => setFeeStatusFilter(e.target.value)}
          aria-label="Filter by fee status"
          className={filterSelectClass}
        >
          <option value="all">All fee statuses</option>
          <option value="pending">Pending balance</option>
          <option value="paid">Fully paid</option>
        </select>

        <select
          value={methodFilter}
          onChange={(e) => setMethodFilter(e.target.value)}
          aria-label="Filter by payment method"
          className={filterSelectClass}
        >
          <option value="all">All methods</option>
          {PAYMENT_METHOD_FILTERS.map((m) => (
            <option key={m.value} value={m.value}>
              {m.label}
            </option>
          ))}
        </select>
      </div>

      <div className="p-6 pt-4">
        <Card className="overflow-hidden">
          {transactions.isPending && <LoadingState label="Loading transactions…" />}

          {transactions.isError && (
            <ErrorState
              description={
                transactions.error instanceof ApiError
                  ? transactions.error.detail
                  : "Could not load transactions."
              }
              onRetry={() => transactions.refetch()}
            />
          )}

          {transactions.data && transactions.data.length === 0 && (
            <EmptyState
              icon={<Banknote className="size-6" />}
              title="No payments recorded yet"
              description="Record one from a student's detail panel to see it here."
            />
          )}

          {visibleTransactions.length > 0 && (
            <div className="scroll-x">
              <table className="w-full min-w-[940px] text-sm">
                <thead>
                  <tr className="border-b border-line-subtle bg-subtle/60 text-left">
                    {[
                      "Receipt", "Student", "Amount", "Paid", "Pending",
                      ...(isAdmin ? ["Collected by"] : []),
                      "Method", "Date", "",
                    ].map((h) => (
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
                  {paging.pageItems.map((t) => (
                    <tr key={t.id} className="border-b border-line-subtle last:border-0">
                      <td className="px-4 py-3 font-mono text-xs text-fg-secondary">
                        {t.receipt_number}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <Avatar name={studentName(t.student_id)} size="sm" />
                          <span className="font-medium text-fg">{studentName(t.student_id)}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3 font-semibold text-fg">{money(t.amount)}</td>
                      {/* The student's overall position, not this one payment —
                          a ledger row alone never says what is still owed. */}
                      <td className="px-4 py-3 tabular-nums text-fg-secondary">
                        {studentById.has(t.student_id)
                          ? money(studentById.get(t.student_id).fees_paid)
                          : "—"}
                      </td>
                      <td className="px-4 py-3 tabular-nums font-semibold">
                        {studentById.has(t.student_id) ? (
                          balanceOf(studentById.get(t.student_id)) > 0 ? (
                            <span className="text-warn-text">
                              {money(balanceOf(studentById.get(t.student_id)))}
                            </span>
                          ) : (
                            <span className="text-success-text">Settled</span>
                          )
                        ) : (
                          "—"
                        )}
                      </td>
                      {/* Attribution, admin only: an HR's ledger is entirely
                          their own, so the column would say the same name on
                          every row. `owner_id` is who the revenue is credited
                          to, which is the question the admin is asking. */}
                      {isAdmin && (
                        <td className="px-4 py-3 text-xs text-fg-secondary">
                          {staffName(t.owner_id)}
                        </td>
                      )}
                      <td className="px-4 py-3">
                        <Badge
                          tone={t.method ? METHOD_TONE[t.method] : "neutral"}
                          className="uppercase"
                        >
                          {(t.method ?? "—").replace("_", " ")}
                        </Badge>
                      </td>
                      <td className="px-4 py-3 text-xs text-fg-muted">
                        {t.created_at ? shortDate(t.created_at) : "—"}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-3">
                          <a
                            href={paymentsApi.receiptUrl(t.id)}
                            className="flex items-center gap-1 text-xs font-semibold text-[var(--brand-text)] hover:underline"
                          >
                            <Download className="size-3.5" /> Receipt
                          </a>
                          {canEdit(studentById.get(t.student_id)) && (
                            <button
                              type="button"
                              onClick={() => setEditFeeFor(studentById.get(t.student_id))}
                              className="flex items-center gap-1 text-xs font-semibold text-fg-secondary hover:text-fg hover:underline"
                            >
                              <Pencil className="size-3.5" aria-hidden /> Edit fee
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Filters can empty the table even though transactions exist —
              say so, rather than showing a bare header row. */}
          {transactions.data &&
            transactions.data.length > 0 &&
            visibleTransactions.length === 0 && (
              <EmptyState
                icon={<Banknote className="size-6" />}
                title="No matching transactions"
                description="Try a different college, method, or search term."
              />
            )}

          {visibleTransactions.length > 0 && <Pagination {...paging} label="transactions" />}
        </Card>
      </div>

      {recordFor && (
        <RecordPaymentDialog
          students={(students.data ?? []).filter(canEdit)}
          balanceOf={balanceOf}
          onClose={() => setRecordFor(null)}
          onDone={refreshMoney}
        />
      )}
      {editFeeFor && (
        <EditFeeDialog
          student={editFeeFor}
          onClose={() => setEditFeeFor(null)}
          onDone={refreshMoney}
        />
      )}
    </>
  );
}

/** Record an installment against a student, without leaving Finance. */
function RecordPaymentDialog({ students, balanceOf, onClose, onDone }) {
  const [studentId, setStudentId] = useState("");
  const [amount, setAmount] = useState("");
  const [method, setMethod] = useState("cash");
  const chosen = students.find((s) => s.id === studentId);
  const owing = balanceOf(chosen);

  const record = useMutation({
    mutationFn: () =>
      paymentsApi.record({ student_id: studentId, amount: Number(amount), method }),
    onSuccess: async (payment) => {
      await onDone();
      onClose();
      // The API caps a payment at the outstanding balance, so say when the
      // recorded figure differs from what was typed rather than letting the
      // ledger quietly disagree with the operator.
      toast.success(
        payment.amount < Number(amount)
          ? `Capped at the ${money(payment.amount)} balance — receipt ${payment.receipt_number}.`
          : `Payment recorded — receipt ${payment.receipt_number}.`,
      );
    },
    onError: (err) =>
      toast.error(err instanceof ApiError ? err.detail : "Could not record the payment."),
  });

  return (
    <Dialog
      open
      onOpenChange={(o) => !o && onClose()}
      title="Record payment"
      description="Only students you claimed appear here."
    >
      <div className="flex flex-col gap-4">
        <Field label="Student" required>
          <select
            className={filterSelectClass + " w-full"}
            value={studentId}
            onChange={(e) => setStudentId(e.target.value)}
          >
            <option value="">Select a student…</option>
            {students.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name} — {money(balanceOf(s))} pending
              </option>
            ))}
          </select>
        </Field>

        {chosen && (
          <dl className="grid grid-cols-2 gap-1 rounded-lg border border-line bg-subtle p-3 text-sm">
            <dt className="text-fg-muted">Total fee</dt>
            <dd className="text-right tabular-nums text-fg">{money(chosen.total_fees)}</dd>
            <dt className="text-fg-muted">Paid so far</dt>
            <dd className="text-right tabular-nums text-fg">{money(chosen.fees_paid)}</dd>
            <dt className="text-fg-muted">Pending</dt>
            <dd
              className={`text-right font-semibold tabular-nums ${
                owing > 0 ? "text-warn-text" : "text-success-text"
              }`}
            >
              {owing > 0 ? money(owing) : "Settled"}
            </dd>
          </dl>
        )}

        <div className="grid grid-cols-2 gap-3">
          <Field label="Amount" required>
            <Input
              type="number"
              min="1"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              placeholder={chosen ? String(owing) : "0"}
            />
          </Field>
          <Field label="Method">
            <select
              className={filterSelectClass + " w-full"}
              value={method}
              onChange={(e) => setMethod(e.target.value)}
            >
              <option value="cash">Cash</option>
              <option value="upi">UPI</option>
            </select>
          </Field>
        </div>

        <div className="mt-2 flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button
            onClick={() => record.mutate()}
            loading={record.isPending}
            disabled={!studentId || !(Number(amount) > 0)}
          >
            Record
          </Button>
        </div>
      </div>
    </Dialog>
  );
}

/** Adjust a student's total fee — and with it, what is still pending. */
function EditFeeDialog({ student, onClose, onDone }) {
  const [total, setTotal] = useState(String(student.total_fees ?? 0));
  const paid = student.fees_paid ?? 0;
  const parsed = Number(total);
  // The fee can never drop below what has been collected: that would read as
  // settled while leaving the student credited against their next payment.
  const tooLow = Number.isFinite(parsed) && parsed < paid;
  const pending = Number.isFinite(parsed) ? Math.max(0, parsed - paid) : 0;

  const save = useMutation({
    mutationFn: () => studentsApi.update(student.id, { total_fees: parsed }),
    onSuccess: async () => {
      await onDone();
      onClose();
      toast.success(`${student.name}: fee set to ${money(parsed)}.`);
    },
    onError: (err) =>
      toast.error(err instanceof ApiError ? err.detail : "Could not update the fee."),
  });

  return (
    <Dialog
      open
      onOpenChange={(o) => !o && onClose()}
      title={`Edit fee — ${student.name}`}
      description="Changes what this student owes. Payments already recorded are untouched."
    >
      <div className="flex flex-col gap-4">
        <Field
          label="Total course fee"
          required
          error={tooLow ? `Cannot be below the ${money(paid)} already paid.` : undefined}
        >
          <Input
            type="number"
            min={paid}
            autoFocus
            value={total}
            onChange={(e) => setTotal(e.target.value)}
          />
        </Field>

        <dl className="grid grid-cols-2 gap-1 rounded-lg border border-line bg-subtle p-3 text-sm">
          <dt className="text-fg-muted">Already paid</dt>
          <dd className="text-right tabular-nums text-fg">{money(paid)}</dd>
          <dt className="text-fg-muted">Pending after this change</dt>
          <dd
            className={`text-right font-semibold tabular-nums ${
              pending > 0 ? "text-warn-text" : "text-success-text"
            }`}
          >
            {pending > 0 ? money(pending) : "Settled"}
          </dd>
        </dl>

        <div className="mt-2 flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button
            onClick={() => save.mutate()}
            loading={save.isPending}
            disabled={tooLow || !Number.isFinite(parsed) || parsed < 0}
          >
            Save fee
          </Button>
        </div>
      </div>
    </Dialog>
  );
}
