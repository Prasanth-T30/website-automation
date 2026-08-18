import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Award, Download, GraduationCap, Plus, Search, Send } from "lucide-react";
import { useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";
import { PageHeader } from "@/components/PageHeader";
import { Avatar } from "@/components/ui/Avatar";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Dialog } from "@/components/ui/Dialog";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Pagination, usePagination } from "@/components/ui/Pagination";
import { SlideOver } from "@/components/ui/SlideOver";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/States";
import { attendanceApi } from "@/features/attendance/api";
import { useAuth } from "@/features/auth/AuthProvider";
import { batchesApi } from "@/features/batches/api";
import { paymentsApi } from "@/features/payments/api";
import { publicApi } from "@/features/public/api";
import { studentsApi } from "@/features/students/api";
import { usersApi } from "@/features/users/api";
import { ApiError } from "@/lib/api";
import { money, shortDate } from "@/lib/format";
const PAYMENT_METHODS = [
  { value: "cash", label: "Cash" },
  { value: "upi", label: "UPI" },
  { value: "bank_transfer", label: "Bank Transfer" },
  { value: "card", label: "Card" },
  { value: "other", label: "Other" },
];
const STUDENTS_KEY = ["students"];

/** Matches Input's styling so native selects don't look out of place. */
const selectClass =
  "h-10 w-full rounded-md border border-line bg-surface px-3 text-sm text-fg outline-none " +
  "transition-colors focus:border-brand";

const addStudentSchema = z
  .object({
    name: z.string().min(2, "Enter the student's name."),
    email: z.string().email("Enter a valid email."),
    phone: z.string().refine((v) => v.replace(/\D/g, "").length >= 10, "Enter a valid mobile."),
    college: z.string().min(2, "Enter the college."),
    place: z.string().min(2, "Enter the place."),
    category: z.string().min(1, "Choose a category."),
    domain: z.string().min(1, "Choose a domain."),
    duration: z.string().min(1, "Choose a duration."),
    batch_id: z.string().optional(),
    total_fees: z.coerce.number().min(0),
    fees_paid: z.coerce.number().min(0),
  })
  // Mirrors the API's own guard, so the mistake is caught before the round trip.
  .refine((v) => v.fees_paid <= v.total_fees, {
    message: "Paid cannot exceed the total fees.",
    path: ["fees_paid"],
  });
const PAY_TONE = {
  paid: "success",
  pending: "warn",
  overdue: "danger",
};
const STATUS_TONE = {
  active: "brand",
  completed: "success",
  dropped: "neutral",
};
export default function Students() {
  const { user, isAdmin } = useAuth();
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [collegeFilter, setCollegeFilter] = useState("all");
  const [selected, setSelected] = useState(null);
  const [createOpen, setCreateOpen] = useState(false);
  const students = useQuery({ queryKey: STUDENTS_KEY, queryFn: () => studentsApi.list() });
  const batches = useQuery({ queryKey: ["batches"], queryFn: () => batchesApi.list() });
  const allUsers = useQuery({
    queryKey: ["admin", "users"],
    queryFn: usersApi.list,
    enabled: isAdmin,
    staleTime: 5 * 60_000,
  });
  const batchCode = (id) => batches.data?.find((b) => b.id === id)?.code ?? "—";
  const ownerName = (id) => allUsers.data?.find((u) => u.id === id)?.full_name ?? id;
  // Derived from the loaded rows rather than a fixed list — colleges arrive
  // as free text on the registration form, so the only accurate set is
  // whatever actually turned up.
  const colleges = useMemo(() => {
    const seen = new Set((students.data ?? []).map((s) => s.college).filter(Boolean));
    return [...seen].sort((a, b) => a.localeCompare(b));
  }, [students.data]);

  const filtered = useMemo(() => {
    const rows = students.data ?? [];
    const q = query.trim().toLowerCase();
    return rows.filter((s) => {
      if (statusFilter !== "all" && s.status !== statusFilter) return false;
      if (collegeFilter !== "all" && s.college !== collegeFilter) return false;
      if (!q) return true;
      return (
        s.name.toLowerCase().includes(q) ||
        s.college.toLowerCase().includes(q) ||
        s.email.toLowerCase().includes(q)
      );
    });
  }, [students.data, query, statusFilter, collegeFilter]);

  const paging = usePagination(filtered);
  return (
    <>
      <PageHeader
        title="Students"
        description={
          students.data
            ? `${students.data.length} students across every batch and the unassigned pool.`
            : undefined
        }
        action={
          <Button onClick={() => setCreateOpen(true)}>
            <Plus className="size-4" /> Add student
          </Button>
        }
      />

      <div className="flex flex-wrap items-center gap-3 px-6 pt-4">
        <div className="relative w-full max-w-xs">
          <Search className="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-fg-muted" />
          <Input
            className="pl-9"
            placeholder="Search name, email, college…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
        <div className="flex gap-1">
          {["all", "active", "completed", "dropped"].map((s) => (
            <button
              key={s}
              onClick={() => setStatusFilter(s)}
              className={`rounded-md px-3 py-1.5 text-xs font-semibold capitalize transition-colors ${statusFilter === s ? "bg-brand text-on-brand" : "text-fg-secondary hover:bg-subtle"}`}
            >
              {s}
            </button>
          ))}
        </div>

        <select
          value={collegeFilter}
          onChange={(e) => setCollegeFilter(e.target.value)}
          aria-label="Filter by college"
          className="h-9 max-w-[16rem] rounded-md border border-line bg-surface px-2.5 text-xs font-semibold text-fg-secondary outline-none focus:border-brand"
        >
          <option value="all">All colleges</option>
          {colleges.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
      </div>

      <div className="p-6 pt-4">
        <Card className="overflow-hidden">
          {students.isPending && <LoadingState label="Loading students…" />}

          {students.isError && (
            <ErrorState
              description={
                students.error instanceof ApiError
                  ? students.error.detail
                  : "Could not load students."
              }
              onRetry={() => students.refetch()}
            />
          )}

          {students.data && filtered.length === 0 && (
            <EmptyState
              icon={<GraduationCap className="size-6" />}
              title="No students found"
              description="Approved applications appear here automatically."
            />
          )}

          {filtered.length > 0 && (
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
                  {paging.pageItems.map((s) => {
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
                              <p className="text-xs text-fg-muted">{s.domain}</p>
                            </div>
                          </div>
                        </td>
                        <td className="px-4 py-3 text-fg-secondary">{s.college}</td>
                        <td className="px-4 py-3">
                          {s.batch_id ? (
                            <Badge tone="neutral">{batchCode(s.batch_id)}</Badge>
                          ) : (
                            <span className="text-xs text-fg-muted">Unassigned</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-xs text-fg-secondary">
                          {isAdmin ? ownerName(s.owner_id) : "—"}
                        </td>
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

          {filtered.length > 0 && <Pagination {...paging} label="students" />}
        </Card>
      </div>

      <SlideOver
        open={selected !== null}
        onOpenChange={(o) => !o && setSelected(null)}
        title={selected?.name ?? ""}
        description={selected ? `${selected.domain} · ${selected.category}` : undefined}
      >
        {selected && (
          <StudentDetail
            student={selected}
            batches={batches.data ?? []}
            ownerName={isAdmin ? ownerName(selected.owner_id) : undefined}
            canRecordPayment={isAdmin || selected.owner_id === user?.id}
            onUpdated={(s) => setSelected(s)}
          />
        )}
      </SlideOver>

      <AddStudentDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        batches={batches.data ?? []}
      />
    </>
  );
}

/** Enrols someone who never went through the public form — a walk-in, or a
 *  phone enquiry an HR closed themselves. */
function AddStudentDialog({ open, onOpenChange, batches }) {
  const queryClient = useQueryClient();
  const choices = useQuery({
    queryKey: ["public", "choices"],
    queryFn: publicApi.choices,
    staleTime: 10 * 60_000,
  });

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm({
    resolver: zodResolver(addStudentSchema),
    defaultValues: { total_fees: 0, fees_paid: 0 },
  });

  const create = useMutation({
    mutationFn: (values) =>
      studentsApi.create({
        ...values,
        batch_id: values.batch_id || null,
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: STUDENTS_KEY });
      await queryClient.invalidateQueries({ queryKey: ["batches"] });
      onOpenChange(false);
      reset({ total_fees: 0, fees_paid: 0 });
      toast.success("Student added.");
    },
    onError: (err) =>
      toast.error(err instanceof ApiError ? err.detail : "Could not add the student."),
  });

  return (
    <Dialog
      open={open}
      onOpenChange={onOpenChange}
      title="Add a student"
      description="For someone who enrolled directly, without going through the registration form."
      footer={
        <>
          <Button variant="secondary" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button form="add-student" type="submit" loading={isSubmitting || create.isPending}>
            Add student
          </Button>
        </>
      }
    >
      <form
        id="add-student"
        onSubmit={handleSubmit((v) => create.mutate(v))}
        className="grid grid-cols-1 gap-4 sm:grid-cols-2"
      >
        <Field label="Full name" required error={errors.name?.message}>
          <Input placeholder="Priya Raman" {...register("name")} />
        </Field>
        <Field label="Email" required error={errors.email?.message}>
          <Input type="email" placeholder="priya@example.com" {...register("email")} />
        </Field>
        <Field label="Phone" required error={errors.phone?.message}>
          <Input placeholder="9876543210" {...register("phone")} />
        </Field>
        <Field label="College" required error={errors.college?.message}>
          <Input placeholder="PSG College of Technology" {...register("college")} />
        </Field>
        <Field label="Place" required error={errors.place?.message}>
          <Input placeholder="Coimbatore" {...register("place")} />
        </Field>
        <Field label="Category" required error={errors.category?.message}>
          <select className={selectClass} {...register("category")}>
            <option value="">Select…</option>
            {(choices.data?.categories ?? []).map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Domain" required error={errors.domain?.message} className="sm:col-span-2">
          <select className={selectClass} {...register("domain")}>
            <option value="">Select…</option>
            {(choices.data?.domains ?? []).map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Duration" required error={errors.duration?.message}>
          <select className={selectClass} {...register("duration")}>
            <option value="">Select…</option>
            {(choices.data?.durations ?? []).map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Batch" hint="Can be assigned later." error={errors.batch_id?.message}>
          <select className={selectClass} {...register("batch_id")}>
            <option value="">Unassigned</option>
            {batches
              .filter((b) => b.status !== "completed")
              .map((b) => (
                <option key={b.id} value={b.id}>
                  {b.code} · {b.domain}
                </option>
              ))}
          </select>
        </Field>
        <Field label="Total fees" required error={errors.total_fees?.message}>
          <Input type="number" min="0" step="500" {...register("total_fees")} />
        </Field>
        <Field
          label="Already paid"
          hint="Leave at 0 to collect later."
          error={errors.fees_paid?.message}
        >
          <Input type="number" min="0" step="500" {...register("fees_paid")} />
        </Field>
      </form>
    </Dialog>
  );
}

function StudentDetail({ student, batches, ownerName, canRecordPayment, onUpdated }) {
  const queryClient = useQueryClient();
  const balance = student.total_fees - student.fees_paid;
  const payments = useQuery({
    queryKey: ["payments", { student_id: student.id }],
    queryFn: () => paymentsApi.list({ student_id: student.id }),
  });
  const attendance = useQuery({
    queryKey: ["attendance", { student_id: student.id }],
    queryFn: () => attendanceApi.list({ student_id: student.id }),
  });
  const presentPct =
    attendance.data && attendance.data.length > 0
      ? Math.round(
          (attendance.data.filter((a) => a.status === "present").length / attendance.data.length) *
            100,
        )
      : null;
  const assignBatch = useMutation({
    mutationFn: (batch_id) => studentsApi.update(student.id, { batch_id }),
    onSuccess: async (updated) => {
      await queryClient.invalidateQueries({ queryKey: STUDENTS_KEY });
      await queryClient.invalidateQueries({ queryKey: ["batches"] });
      onUpdated(updated);
      toast.success("Batch updated.");
    },
    onError: (err) => toast.error(err instanceof ApiError ? err.detail : "Could not update batch."),
  });
  const [previewOpen, setPreviewOpen] = useState(false);
  const issueCertificate = useMutation({
    mutationFn: () => studentsApi.issueCertificate(student.id),
    onSuccess: async (result) => {
      await queryClient.invalidateQueries({ queryKey: ["reports"] });
      setPreviewOpen(false);
      // The certificate is filed even when the email can't go out, so say
      // which of the two actually happened rather than a bare "Done".
      if (result.email_sent) {
        toast.success(`Certificate ${result.certificate_number} emailed to ${result.emailed_to}.`);
      } else {
        toast.success(
          `Certificate ${result.certificate_number} generated and filed under Documents. ` +
            `Email was not sent — SMTP is not configured.`,
        );
      }
    },
    onError: (err) =>
      toast.error(err instanceof ApiError ? err.detail : "Could not issue the certificate."),
  });

  const [amount, setAmount] = useState("");
  const [method, setMethod] = useState("cash");
  const recordPayment = useMutation({
    mutationFn: () =>
      paymentsApi.record({ student_id: student.id, amount: Number(amount), method }),
    onSuccess: async (payment) => {
      await queryClient.invalidateQueries({ queryKey: STUDENTS_KEY });
      await queryClient.invalidateQueries({ queryKey: ["payments", { student_id: student.id }] });
      const updated = await studentsApi.get(student.id);
      onUpdated(updated);
      setAmount("");
      toast.success(
        payment.amount < Number(amount)
          ? `Capped at the ${money(payment.amount)} balance — receipt ${payment.receipt_number}.`
          : `Payment recorded — receipt ${payment.receipt_number}.`,
      );
    },
    onError: (err) =>
      toast.error(err instanceof ApiError ? err.detail : "Could not record payment."),
  });
  return (
    <div className="flex flex-col gap-5 p-5">
      <div className="flex items-center gap-3">
        <Avatar name={student.name} size="lg" />
        <div>
          <p className="text-sm font-bold text-fg">{student.name}</p>
          <p className="text-xs text-fg-muted">{student.college}</p>
        </div>
      </div>

      <Card>
        <CardBody className="grid grid-cols-2 gap-4 !p-4">
          {[
            ["Email", student.email],
            ["Phone", student.phone],
            ["Place", student.place],
            ["Duration", student.duration],
            ...(ownerName ? [["Owner", ownerName]] : []),
            ["Enrolled", student.created_at ? shortDate(student.created_at) : "—"],
          ].map(([label, value]) => (
            <div key={label}>
              <p className="text-[10px] font-bold tracking-wide text-fg-muted uppercase">{label}</p>
              <p className="mt-0.5 text-sm text-fg">{value}</p>
            </div>
          ))}
        </CardBody>
      </Card>

      <Card>
        <CardHeader title="Batch" description="Assign this student to a training cohort." />
        <CardBody className="!p-4">
          <select
            className="h-10 w-full rounded-md border border-line bg-surface px-3 text-sm text-fg"
            value={student.batch_id ?? ""}
            disabled={assignBatch.isPending}
            onChange={(e) => assignBatch.mutate(e.target.value || null)}
          >
            <option value="">Unassigned</option>
            {batches.map((b) => (
              <option key={b.id} value={b.id}>
                {b.code}
              </option>
            ))}
          </select>
        </CardBody>
      </Card>

      <Card>
        <CardHeader
          title="Payments"
          description={balance > 0 ? `${money(balance)} outstanding` : "Paid in full"}
        />
        <CardBody className="!p-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-[10px] font-bold tracking-wide text-fg-muted uppercase">
                Total fees
              </p>
              <p className="mt-0.5 text-sm font-semibold text-fg">{money(student.total_fees)}</p>
            </div>
            <div>
              <p className="text-[10px] font-bold tracking-wide text-fg-muted uppercase">
                Paid so far
              </p>
              <p className="mt-0.5 text-sm font-semibold text-fg">{money(student.fees_paid)}</p>
            </div>
          </div>

          {canRecordPayment && balance > 0 && (
            <form
              onSubmit={(e) => {
                e.preventDefault();
                if (Number(amount) > 0) recordPayment.mutate();
              }}
              className="mt-4 flex items-end gap-2 border-t border-line-subtle pt-4"
            >
              <div className="flex-1">
                <label className="text-[10px] font-bold tracking-wide text-fg-muted uppercase">
                  Amount
                </label>
                <Input
                  type="number"
                  min={1}
                  step="0.01"
                  placeholder={`Balance ${money(balance)}`}
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                />
              </div>
              <div>
                <label className="text-[10px] font-bold tracking-wide text-fg-muted uppercase">
                  Method
                </label>
                <select
                  className="h-10 rounded-md border border-line bg-surface px-2 text-sm text-fg"
                  value={method}
                  onChange={(e) => setMethod(e.target.value)}
                >
                  {PAYMENT_METHODS.map((m) => (
                    <option key={m.value} value={m.value}>
                      {m.label}
                    </option>
                  ))}
                </select>
              </div>
              <Button type="submit" loading={recordPayment.isPending} disabled={!amount}>
                Record
              </Button>
            </form>
          )}

          {payments.data && payments.data.length > 0 && (
            <ul className="mt-4 divide-y divide-line-subtle border-t border-line-subtle">
              {payments.data.map((p) => (
                <li key={p.id} className="flex items-center justify-between py-2 text-sm">
                  <div>
                    <p className="font-medium text-fg">{money(p.amount)}</p>
                    <p className="text-xs text-fg-muted">
                      {p.receipt_number} · {p.created_at ? shortDate(p.created_at) : "—"}
                    </p>
                  </div>
                  <a
                    href={paymentsApi.receiptUrl(p.id)}
                    className="flex items-center gap-1 text-xs font-semibold text-[var(--brand-text)] hover:underline"
                  >
                    <Download className="size-3.5" /> Receipt
                  </a>
                </li>
              ))}
            </ul>
          )}
        </CardBody>
      </Card>

      {presentPct !== null && (
        <Card>
          <CardHeader
            title="Attendance"
            description={`${attendance.data?.length ?? 0} sessions recorded`}
          />
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

      <Card>
        <CardHeader
          title="Certificate"
          description="Generated from this record — the name and programme come straight from their registration."
        />
        <CardBody className="!p-4">
          {student.status !== "completed" ? (
            <p className="text-xs text-fg-muted">
              Available once this student is marked <span className="font-semibold">completed</span>.
            </p>
          ) : (
            <>
              <Button onClick={() => setPreviewOpen(true)} disabled={!canRecordPayment}>
                <Award className="size-4" /> Generate certificate
              </Button>
              <p className="mt-2 text-xs text-fg-muted">
                {canRecordPayment
                  ? "Opens a preview. Nothing is sent until you confirm."
                  : "Only this student's owner or an admin can issue the certificate."}
              </p>
            </>
          )}
        </CardBody>
      </Card>

      <CertificatePreview
        open={previewOpen}
        onOpenChange={setPreviewOpen}
        student={student}
        onSend={() => issueCertificate.mutate()}
        sending={issueCertificate.isPending}
      />
    </div>
  );
}

/**
 * Review-then-send. The preview streams the same endpoint the email attachment
 * is built from, so what an HR approves here is what the student receives.
 */
function CertificatePreview({ open, onOpenChange, student, onSend, sending }) {
  return (
    <Dialog
      open={open}
      onOpenChange={onOpenChange}
      title={`Certificate — ${student.name}`}
      description={`${student.domain} · ${student.category} · will be emailed to ${student.email}`}
      className="max-w-4xl"
      footer={
        <>
          <a
            href={studentsApi.certificateUrl(student.id)}
            download
            className="mr-auto flex items-center gap-1.5 text-xs font-semibold text-[var(--brand-text)] hover:underline"
          >
            <Download className="size-3.5" /> Download a copy
          </a>
          <Button variant="secondary" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={onSend} loading={sending}>
            <Send className="size-4" /> Send to student
          </Button>
        </>
      }
    >
      <div className="overflow-hidden rounded-md border border-line bg-subtle">
        {/* Served inline, so the browser's own PDF viewer renders it. The
            session cookie rides along because this is same-origin. */}
        <iframe
          key={student.id}
          src={studentsApi.certificateUrl(student.id)}
          title={`Certificate preview for ${student.name}`}
          className="block h-[62vh] w-full"
        />
      </div>
      <p className="mt-3 text-xs text-fg-muted">
        Sending emails this PDF to <span className="font-semibold text-fg-secondary">{student.email}</span>{" "}
        and files a copy under Documents.
      </p>
    </Dialog>
  );
}
