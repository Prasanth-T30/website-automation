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
import { toast } from "sonner";
import { PageHeader } from "@/components/PageHeader";
import { Avatar } from "@/components/ui/Avatar";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardBody } from "@/components/ui/Card";
import { Dialog } from "@/components/ui/Dialog";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Pagination, usePagination } from "@/components/ui/Pagination";
import { SlideOver } from "@/components/ui/SlideOver";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/States";
import { useAuth } from "@/features/auth/AuthProvider";
import { batchesApi } from "@/features/batches/api";
import { paymentsApi } from "@/features/payments/api";
import { studentsApi } from "@/features/students/api";
import { isOverdue } from "@/features/students/overdue";
import { usersApi } from "@/features/users/api";
import { ApiError } from "@/lib/api";
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
  const queryClient = useQueryClient();
  const [collegeFilter, setCollegeFilter] = useState("all");
  const [methodFilter, setMethodFilter] = useState("all");
  const [feeStatusFilter, setFeeStatusFilter] = useState("all");
  const [query, setQuery] = useState("");
  const [openStudent, setOpenStudent] = useState(null);
  const [recordFor, setRecordFor] = useState(null);
  const [editFeeFor, setEditFeeFor] = useState(null);

  // Both come back already scoped: an HR's own students and own transactions,
  // everyone's for an admin.
  const transactions = useQuery({
    queryKey: ["payments", { mine: !isAdmin }],
    queryFn: () => paymentsApi.list(isAdmin ? undefined : { mine: true }),
  });
  const students = useQuery({ queryKey: ["students"], queryFn: () => studentsApi.list() });
  const batches = useQuery({ queryKey: ["batches"], queryFn: () => batchesApi.list() });
  const staff = useQuery({ queryKey: ["users"], queryFn: usersApi.list, enabled: isAdmin });
  const staffName = (id) => (staff.data ?? []).find((u) => u.id === id)?.full_name ?? "—";

  const balanceOf = (s) => (s ? Math.max(0, s.total_fees - s.fees_paid) : 0);
  /** Recording and fee edits belong to whoever claimed the student. The API
   *  enforces this too (403); this only decides whether to offer the control
   *  rather than let someone click into a refusal. */
  const canEdit = (s) => Boolean(s) && (isAdmin || s.owner_id === user?.id);

  /**
   * One row per student, not per transaction.
   *
   * A ledger repeats a name once for every installment, and the fee columns
   * beside it repeat the same student-level total on each of those rows — so
   * three payments looked like three debts. Finance answers "who owes what",
   * which is a question about people; the individual transactions belong in
   * that person's own history, one click away.
   */
  const perStudent = useMemo(() => {
    const byStudent = new Map();
    for (const t of transactions.data ?? []) {
      if (!byStudent.has(t.student_id)) byStudent.set(t.student_id, []);
      byStudent.get(t.student_id).push(t);
    }
    return (students.data ?? [])
      .map((s) => {
        const rows = byStudent.get(s.id) ?? [];
        const latest = rows.reduce(
          (newest, t) =>
            !newest || (t.created_at && t.created_at > newest.created_at) ? t : newest,
          null,
        );
        return {
          student: s,
          payments: rows,
          collected: rows.reduce((sum, t) => sum + t.amount, 0),
          balance: balanceOf(s),
          lastPaidAt: latest?.created_at ?? null,
          methods: new Set(rows.map((t) => t.method ?? "other")),
        };
      })
      .sort((a, b) => b.balance - a.balance || a.student.name.localeCompare(b.student.name));
  }, [transactions.data, students.data]);

  const colleges = useMemo(() => {
    const seen = new Set();
    for (const s of students.data ?? []) if (s.college) seen.add(s.college);
    return [...seen].sort((a, b) => a.localeCompare(b));
  }, [students.data]);

  const visible = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return perStudent.filter((r) => {
      if (collegeFilter !== "all" && r.student.college !== collegeFilter) return false;
      if (feeStatusFilter === "paid" && r.balance > 0) return false;
      if (feeStatusFilter === "pending" && r.balance <= 0) return false;
      // A method belongs to a transaction, so at student level this reads as
      // "has ever paid this way" — which is what someone reconciling a cash
      // book is actually looking for.
      if (methodFilter !== "all" && !r.methods.has(methodFilter)) return false;
      if (!needle) return true;
      return (
        r.student.name.toLowerCase().includes(needle) ||
        r.payments.some((t) => t.receipt_number.toLowerCase().includes(needle))
      );
    });
  }, [perStudent, collegeFilter, feeStatusFilter, methodFilter, query]);

  const paging = usePagination(visible);

  const refreshMoney = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["payments"] }),
      queryClient.invalidateQueries({ queryKey: ["students"] }),
      queryClient.invalidateQueries({ queryKey: ["admin", "hr-performance"] }),
    ]);
  };

  // The export stays a transaction ledger — that is what an accountant needs —
  // but carries the screen's filters so it covers the same people.
  const exportFilters = {
    mine: !isAdmin,
    method: methodFilter,
    college: collegeFilter,
    q: query,
    fee_status: feeStatusFilter,
  };

  const summary = useMemo(() => {
    const batchesById = new Map((batches.data ?? []).map((b) => [b.id, b]));
    const unpaid = perStudent.filter((r) => r.balance > 0);
    const overdue = unpaid.filter((r) => isOverdue(r.student, batchesById));
    return {
      totalRevenue: perStudent.reduce((sum, r) => sum + r.collected, 0),
      pendingAmount: unpaid
        .filter((r) => !isOverdue(r.student, batchesById))
        .reduce((sum, r) => sum + r.balance, 0),
      overdueAmount: overdue.reduce((sum, r) => sum + r.balance, 0),
      paidCount: perStudent.filter((r) => r.balance <= 0).length,
    };
  }, [perStudent, batches.data]);

  const openRow = openStudent ? perStudent.find((r) => r.student.id === openStudent) : null;

  return (
    <>
      <PageHeader
        title="Payments"
        description="What each student owes and has paid. Open a name for their full payment history."
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
          value={String(summary.paidCount)}
          tone="bg-brand-subtle text-brand"
        />
      </div>

      <div className="flex flex-wrap items-center gap-3 px-6">
        <div className="relative w-full max-w-xs">
          <Search className="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-fg-muted" />
          <Input
            className="pl-9"
            placeholder="Search student or receipt…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
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
              Paid by {m.label}
            </option>
          ))}
        </select>
      </div>

      <div className="p-6 pt-4">
        <Card className="overflow-hidden">
          {(students.isPending || transactions.isPending) && (
            <LoadingState label="Loading payments…" />
          )}

          {transactions.isError && (
            <ErrorState
              description={
                transactions.error instanceof ApiError
                  ? transactions.error.detail
                  : "Could not load payments."
              }
              onRetry={() => transactions.refetch()}
            />
          )}

          {students.data && perStudent.length === 0 && (
            <EmptyState
              icon={<Banknote className="size-6" />}
              title="No students yet"
              description="Approve an application to start tracking fees."
            />
          )}

          {visible.length > 0 && (
            <div className="scroll-x">
              <table className="w-full min-w-[860px] text-sm">
                <thead>
                  <tr className="border-b border-line-subtle bg-subtle/60 text-left">
                    {[
                      "Student",
                      "Total fee",
                      "Paid",
                      "Pending",
                      "Payments",
                      ...(isAdmin ? ["HR"] : []),
                      "Last payment",
                      "",
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
                  {paging.pageItems.map((r) => (
                    <tr
                      key={r.student.id}
                      onClick={() => setOpenStudent(r.student.id)}
                      className="cursor-pointer border-b border-line-subtle transition-colors last:border-0 hover:bg-subtle/60"
                    >
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <Avatar name={r.student.name} size="sm" />
                          <div className="min-w-0">
                            <p className="truncate font-medium text-fg">{r.student.name}</p>
                            <p className="truncate text-xs text-fg-muted">{r.student.college}</p>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3 tabular-nums text-fg-secondary">
                        {money(r.student.total_fees)}
                      </td>
                      <td className="px-4 py-3 font-semibold tabular-nums text-fg">
                        {money(r.student.fees_paid)}
                      </td>
                      <td className="px-4 py-3 tabular-nums font-semibold">
                        {r.balance > 0 ? (
                          <span className="text-warn-text">{money(r.balance)}</span>
                        ) : (
                          <span className="text-success-text">Settled</span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <Badge tone={r.payments.length ? "brand" : "neutral"}>
                          {r.payments.length}
                        </Badge>
                      </td>
                      {isAdmin && (
                        <td className="px-4 py-3 text-xs text-fg-secondary">
                          {staffName(r.student.owner_id)}
                        </td>
                      )}
                      <td className="px-4 py-3 text-xs text-fg-muted">
                        {r.lastPaidAt ? shortDate(r.lastPaidAt) : "—"}
                      </td>
                      <td className="px-4 py-3">
                        {canEdit(r.student) && (
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              setEditFeeFor(r.student);
                            }}
                            className="flex items-center gap-1 text-xs font-semibold text-fg-secondary hover:text-fg hover:underline"
                          >
                            <Pencil className="size-3.5" aria-hidden /> Edit fee
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Filters can empty the table even though students exist — say so,
              rather than showing a bare header row. */}
          {perStudent.length > 0 && visible.length === 0 && (
            <EmptyState
              icon={<Banknote className="size-6" />}
              title="No matching students"
              description="Try a different college, fee status, method, or search term."
            />
          )}

          {visible.length > 0 && <Pagination {...paging} label="students" />}
        </Card>
      </div>

      {openRow && (
        <StudentPayments
          row={openRow}
          canEdit={canEdit(openRow.student)}
          ownerName={isAdmin ? staffName(openRow.student.owner_id) : null}
          onClose={() => setOpenStudent(null)}
          onRecord={() => {
            setRecordFor({ preselect: openRow.student.id });
            setOpenStudent(null);
          }}
          onEditFee={() => {
            setEditFeeFor(openRow.student);
            setOpenStudent(null);
          }}
        />
      )}

      {recordFor && (
        <RecordPaymentDialog
          students={(students.data ?? []).filter(canEdit)}
          preselect={recordFor.preselect}
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

/** Everything about one student's money: where they stand, and every
 *  transaction that got them there. */
function StudentPayments({ row, canEdit, ownerName, onClose, onRecord, onEditFee }) {
  const { student, payments, balance } = row;
  const ordered = [...payments].sort((a, b) =>
    (b.created_at ?? "").localeCompare(a.created_at ?? ""),
  );

  return (
    <SlideOver open onOpenChange={(o) => !o && onClose()} title={student.name}>
      <div className="flex flex-col gap-5 p-5">
        <Card>
          <CardBody className="flex flex-col gap-3">
            <div className="grid grid-cols-2 gap-3">
              <div className="rounded-md border border-line-subtle bg-subtle p-3">
                <p className="text-[10px] font-bold tracking-wide text-fg-muted uppercase">Paid</p>
                <p className="mt-0.5 text-lg font-extrabold tabular-nums text-success-text">
                  {money(student.fees_paid)}
                </p>
              </div>
              <div className="rounded-md border border-line-subtle bg-subtle p-3">
                <p className="text-[10px] font-bold tracking-wide text-fg-muted uppercase">
                  Pending
                </p>
                <p
                  className={`mt-0.5 text-lg font-extrabold tabular-nums ${
                    balance > 0 ? "text-warn-text" : "text-success-text"
                  }`}
                >
                  {balance > 0 ? money(balance) : "Settled"}
                </p>
              </div>
            </div>

            <dl className="grid grid-cols-2 gap-2 text-sm">
              <dt className="text-fg-muted">Total fee</dt>
              <dd className="text-right tabular-nums text-fg">{money(student.total_fees)}</dd>
              <dt className="text-fg-muted">Programme</dt>
              <dd className="text-right text-fg">{student.domain ?? "—"}</dd>
              <dt className="text-fg-muted">College</dt>
              <dd className="truncate text-right text-fg">{student.college ?? "—"}</dd>
              {ownerName && (
                <>
                  <dt className="text-fg-muted">Claimed by</dt>
                  <dd className="text-right text-fg">{ownerName}</dd>
                </>
              )}
            </dl>

            {canEdit && (
              <div className="flex gap-2">
                <Button size="sm" onClick={onRecord} className="flex-1">
                  <Plus className="size-3.5" aria-hidden /> Record payment
                </Button>
                <Button size="sm" variant="secondary" onClick={onEditFee} className="flex-1">
                  <Pencil className="size-3.5" aria-hidden /> Edit fee
                </Button>
              </div>
            )}
          </CardBody>
        </Card>

        <div>
          <h3 className="mb-2 text-xs font-bold tracking-wide text-fg-muted uppercase">
            Payment history ({ordered.length})
          </h3>

          {ordered.length === 0 && (
            <p className="rounded-md border border-line-subtle px-3 py-6 text-center text-xs text-fg-muted">
              Nothing recorded yet — the whole fee is outstanding.
            </p>
          )}

          {ordered.length > 0 && (
            <ul className="divide-y divide-line-subtle rounded-md border border-line-subtle">
              {ordered.map((t) => (
                <li key={t.id} className="flex items-center gap-3 px-3 py-2.5">
                  <div className="min-w-0 flex-1">
                    <p className="font-mono text-xs text-fg-secondary">{t.receipt_number}</p>
                    <p className="text-[11px] text-fg-muted">
                      {t.created_at ? shortDate(t.created_at) : "—"}
                    </p>
                  </div>
                  <Badge tone={t.method ? METHOD_TONE[t.method] : "neutral"} className="uppercase">
                    {(t.method ?? "—").replace("_", " ")}
                  </Badge>
                  <span className="w-24 text-right font-semibold tabular-nums text-fg">
                    {money(t.amount)}
                  </span>
                  <a
                    href={paymentsApi.receiptUrl(t.id)}
                    className="text-fg-muted transition-colors hover:text-fg"
                    aria-label={`Download receipt ${t.receipt_number}`}
                  >
                    <Download className="size-4" aria-hidden />
                  </a>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </SlideOver>
  );
}

/** Record an installment against a student, without leaving Finance. */
function RecordPaymentDialog({ students, preselect, balanceOf, onClose, onDone }) {
  const [studentId, setStudentId] = useState(preselect ?? "");
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
            className={filterSelectClass + " w-full max-w-none"}
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
              className={filterSelectClass + " w-full max-w-none"}
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
