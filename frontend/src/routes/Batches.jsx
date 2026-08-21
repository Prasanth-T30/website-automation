import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Banknote, Layers, Plus, UserMinus, UserPlus, Users } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";
import { PageHeader } from "@/components/PageHeader";
import { Avatar } from "@/components/ui/Avatar";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardBody } from "@/components/ui/Card";
import { Dialog } from "@/components/ui/Dialog";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { SlideOver } from "@/components/ui/SlideOver";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/States";
import { batchesApi } from "@/features/batches/api";
import { publicApi } from "@/features/public/api";
import { studentsApi } from "@/features/students/api";
import { useAuth } from "@/features/auth/AuthProvider";
import { ApiError } from "@/lib/api";
import { cn } from "@/lib/cn";
import { money, shortDate } from "@/lib/format";
const BATCHES_KEY = ["batches"];
const TONE = {
  active: "brand",
  completed: "success",
  upcoming: "warn",
};
const createSchema = z.object({
  code: z.string().min(2, "Give the batch a short code.").max(30),
  domain: z.string().min(1, "Choose a domain."),
  start_date: z.string().min(1, "Pick a start date."),
  end_date: z.string().min(1, "Pick an end date."),
  capacity: z.coerce.number().int().min(1).max(500),
  notes: z.string().optional(),
});
export default function Batches() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [selected, setSelected] = useState(null);
  const [createOpen, setCreateOpen] = useState(false);
  const batches = useQuery({ queryKey: BATCHES_KEY, queryFn: () => batchesApi.list() });
  const choices = useQuery({ queryKey: ["public", "choices"], queryFn: publicApi.choices });
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm({ resolver: zodResolver(createSchema), defaultValues: { capacity: 20 } });
  const createBatch = useMutation({
    mutationFn: (values) => batchesApi.create(values),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: BATCHES_KEY });
      setCreateOpen(false);
      reset({ capacity: 20 });
      toast.success("Batch created.");
    },
    onError: (err) => toast.error(err instanceof ApiError ? err.detail : "Could not create batch."),
  });
  return (
    <>
      <PageHeader
        title="Batches"
        description={
          batches.data
            ? `${batches.data.length} batches — ${batches.data.filter((b) => b.status === "active").length} currently active.`
            : undefined
        }
        action={
          /* Any HR can open a cohort — they own the one they create. */
          <Button onClick={() => setCreateOpen(true)}>
            <Plus className="size-4" /> Add batch
          </Button>
        }
      />

      <div className="p-6">
        {batches.isPending && <LoadingState label="Loading batches…" />}

        {batches.isError && (
          <ErrorState
            description={
              batches.error instanceof ApiError ? batches.error.detail : "Could not load batches."
            }
            onRetry={() => batches.refetch()}
          />
        )}

        {batches.data?.length === 0 && (
          <EmptyState
            icon={<Layers className="size-6" />}
            title="No batches yet"
            description="Create the first batch to start assigning students."
          />
        )}

        {batches.data && batches.data.length > 0 && (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {batches.data.map((b) => {
              // Authorship, not can_edit: an admin can edit every batch, so
              // keying the highlight off permission would light up the whole
              // page for them and mark nothing out.
              const mine = b.created_by_id && b.created_by_id === user?.id;
              return (
              <Card
                key={b.id}
                className={cn(
                  "cursor-pointer transition-shadow hover:shadow-e2",
                  mine && "ring-2 ring-brand/45",
                )}
                onClick={() => setSelected(b)}
              >
                <CardBody className="flex flex-col gap-3">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <p className="text-sm font-bold text-fg">{b.code}</p>
                      <p className="text-xs text-fg-muted">{b.domain}</p>
                    </div>
                    <div className="flex shrink-0 items-center gap-1.5">
                      {mine && <Badge tone="brand">Yours</Badge>}
                      <Badge tone={TONE[b.status]} className="capitalize">
                        {b.status}
                      </Badge>
                    </div>
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
                      <span
                        className={
                          b.days_left <= 7 ? "ml-1.5 font-semibold text-danger-text" : "ml-1.5"
                        }
                      >
                        · {b.days_left}d left
                      </span>
                    )}
                  </p>

                  {/* Batches are shared across the team, so each card names the
                    HR who owns it — only they and an admin can change it. */}
                  <div className="flex items-center justify-between gap-2 border-t border-line-subtle pt-2.5">
                    <span className="truncate text-[11px] text-fg-muted">
                      {mine
                        ? "Created by you"
                        : b.created_by_name
                          ? `Created by ${b.created_by_name}`
                          : "Created by —"}
                    </span>
                    {!b.can_edit && (
                      <span className="shrink-0 text-[10px] font-bold tracking-wide text-fg-muted uppercase">
                        View only
                      </span>
                    )}
                  </div>
                </CardBody>
              </Card>
              );
            })}
          </div>
        )}
      </div>

      <SlideOver
        open={selected !== null}
        onOpenChange={(o) => !o && setSelected(null)}
        title={selected?.code ?? ""}
        description={selected?.domain}
      >
        {selected && <BatchRoster batch={selected} />}
      </SlideOver>

      <Dialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        title="Add a batch"
        description="Batches group students for attendance and scheduling."
      >
        <form
          onSubmit={handleSubmit((v) => createBatch.mutateAsync(v))}
          noValidate
          className="flex flex-col gap-4"
        >
          <Field label="Code" error={errors.code?.message} hint="e.g. JAVA-04" required>
            <Input autoFocus {...register("code")} />
          </Field>
          <Field label="Domain" error={errors.domain?.message} required>
            <select
              className="h-10 w-full rounded-md border border-line bg-surface px-3 text-sm text-fg"
              {...register("domain")}
            >
              <option value="">Select…</option>
              {choices.data?.domains.map((d) => (
                <option key={d} value={d}>
                  {d}
                </option>
              ))}
            </select>
          </Field>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Start date" error={errors.start_date?.message} required>
              <Input type="date" {...register("start_date")} />
            </Field>
            <Field label="End date" error={errors.end_date?.message} required>
              <Input type="date" {...register("end_date")} />
            </Field>
          </div>
          <Field label="Capacity" error={errors.capacity?.message} required>
            <Input type="number" min={1} max={500} {...register("capacity")} />
          </Field>
          <Field label="Notes" error={errors.notes?.message}>
            <Input {...register("notes")} />
          </Field>
          <div className="mt-2 flex justify-end gap-2">
            <Button type="button" variant="secondary" onClick={() => setCreateOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" loading={isSubmitting}>
              Create batch
            </Button>
          </div>
        </form>
      </Dialog>
    </>
  );
}
function BatchRoster({ batch }) {
  const queryClient = useQueryClient();
  const { isAdmin } = useAuth();
  const [addOpen, setAddOpen] = useState(false);

  // The roster is everyone in the cohort — the batch is shared, so who is in
  // it is shared too. Fee fields arrive null for other HRs' students, so the
  // amounts never reach this browser at all rather than being hidden here.
  const roster = useQuery({
    queryKey: ["batches", batch.id, "roster"],
    queryFn: () => batchesApi.roster(batch.id),
  });
  const finance = useQuery({
    queryKey: ["batches", batch.id, "finance"],
    queryFn: () => batchesApi.finance(batch.id),
  });
  const allStudents = useQuery({
    queryKey: ["students"],
    queryFn: () => studentsApi.list(),
    enabled: batch.can_edit,
  });

  const rows = roster.data ?? [];
  const f = finance.data;

  const refresh = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["batches"] }),
      queryClient.invalidateQueries({ queryKey: ["students"] }),
    ]);
  };

  const assign = useMutation({
    mutationFn: (studentId) => studentsApi.update(studentId, { batch_id: batch.id }),
    onSuccess: async () => {
      await refresh();
      toast.success("Added to the batch.");
    },
    onError: (err) =>
      toast.error(err instanceof ApiError ? err.detail : "Could not add that student."),
  });
  const unassign = useMutation({
    mutationFn: (studentId) => studentsApi.update(studentId, { batch_id: null }),
    onSuccess: async () => {
      await refresh();
      toast.success("Removed from the batch.");
    },
    onError: (err) =>
      toast.error(err instanceof ApiError ? err.detail : "Could not remove that student."),
  });

  const assignable = (allStudents.data ?? []).filter((s) => !s.batch_id);
  const full = batch.capacity > 0 && batch.student_count >= batch.capacity;
  const balanceOf = (s) => Math.max(0, s.total_fees - s.fees_paid);

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
          <div className="col-span-2 border-t border-line-subtle pt-3">
            <p className="text-[10px] font-bold tracking-wide text-fg-muted uppercase">
              Created by
            </p>
            <p className="mt-0.5 text-sm text-fg">
              {batch.created_by_name ?? "—"}
              {batch.can_edit && (
                <span className="ml-2 text-xs font-semibold text-[var(--brand-text)]">
                  You can edit this
                </span>
              )}
            </p>
          </div>
        </CardBody>
      </Card>

      {/* Money. An HR's figures cover their own students only, so the panel
          says how many of the cohort they describe rather than letting the
          number read as the whole batch's takings. */}
      <Card>
        <CardBody className="flex flex-col gap-3">
          <div className="flex items-center gap-2">
            <Banknote className="size-4 text-fg-muted" />
            <h3 className="text-xs font-bold tracking-wide text-fg-muted uppercase">
              {isAdmin ? "Batch finances" : "Your students in this batch"}
            </h3>
          </div>

          {finance.isPending && <LoadingState label="Loading figures…" />}

          {f && (
            <>
              <div className="grid grid-cols-2 gap-3">
                <div className="rounded-md border border-line-subtle bg-subtle p-3">
                  <p className="text-[10px] font-bold tracking-wide text-fg-muted uppercase">
                    Collected
                  </p>
                  <p className="mt-0.5 text-lg font-extrabold tabular-nums text-success-text">
                    {money(f.collected)}
                  </p>
                </div>
                <div className="rounded-md border border-line-subtle bg-subtle p-3">
                  <p className="text-[10px] font-bold tracking-wide text-fg-muted uppercase">
                    Remaining
                  </p>
                  <p
                    className={`mt-0.5 text-lg font-extrabold tabular-nums ${
                      f.remaining > 0 ? "text-warn-text" : "text-success-text"
                    }`}
                  >
                    {money(f.remaining)}
                  </p>
                </div>
              </div>

              <dl className="grid grid-cols-2 gap-2 text-sm">
                <dt className="text-fg-muted">Fully paid</dt>
                <dd className="text-right font-semibold tabular-nums text-fg">
                  {f.settled_count}
                </dd>
                <dt className="text-fg-muted">Still owing</dt>
                <dd className="text-right font-semibold tabular-nums text-fg">{f.owing_count}</dd>
              </dl>

              {f.counted_students !== f.total_students && (
                <p className="text-xs text-fg-muted">
                  Covers {f.counted_students} of {f.total_students} students — the rest belong to
                  other HRs.
                </p>
              )}
            </>
          )}
        </CardBody>
      </Card>

      <div>
        <div className="mb-2 flex items-center gap-2">
          <Layers className="size-4 text-fg-muted" />
          <h3 className="text-xs font-bold tracking-wide text-fg-muted uppercase">
            Roster {roster.data ? `(${rows.length})` : ""}
          </h3>
          {/* Only the person who set the batch up decides who sits in it. */}
          {batch.can_edit && (
            <Button
              size="sm"
              variant="secondary"
              className="ml-auto"
              onClick={() => setAddOpen(true)}
              disabled={full}
              title={full ? "This batch is full." : undefined}
            >
              <UserPlus className="size-3.5" aria-hidden /> Add
            </Button>
          )}
        </div>

        {full && batch.can_edit && (
          <p className="mb-2 text-xs text-warn-text">
            Full at {batch.student_count} of {batch.capacity}. Remove someone to free a seat.
          </p>
        )}

        {roster.isPending && <LoadingState label="Loading roster…" />}

        {roster.data && (
          <ul className="divide-y divide-line-subtle rounded-md border border-line-subtle">
            {rows.map((s) => (
              <li key={s.id} className="flex items-center gap-2.5 px-3 py-2.5">
                <Avatar name={s.name} size="sm" />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-fg">{s.name}</p>
                  <p className="truncate text-xs text-fg-muted">
                    {/* Fees only for your own; a colleague's student shows
                        their programme instead of a blanked-out figure. */}
                    {s.balance === null || s.balance === undefined
                      ? (s.owner_name ?? s.domain ?? "—")
                      : s.balance > 0
                        ? `${money(s.balance)} pending`
                        : "Settled"}
                  </p>
                </div>
                {s.payment_status && (
                  <Badge
                    tone={
                      s.payment_status === "paid"
                        ? "success"
                        : s.payment_status === "overdue"
                          ? "danger"
                          : "warn"
                    }
                  >
                    {s.payment_status}
                  </Badge>
                )}
                {(batch.can_edit || s.is_mine) && (
                  <button
                    type="button"
                    onClick={() => unassign.mutate(s.id)}
                    disabled={unassign.isPending}
                    aria-label={`Remove ${s.name} from ${batch.code}`}
                    className="rounded p-1 text-fg-muted transition-colors hover:bg-danger-subtle hover:text-danger"
                  >
                    <UserMinus className="size-4" aria-hidden />
                  </button>
                )}
              </li>
            ))}
            {rows.length === 0 && (
              <li className="px-3 py-6 text-center text-xs text-fg-muted">No students yet.</li>
            )}
          </ul>
        )}

        {!batch.can_edit && (
          <p className="mt-2 text-xs text-fg-muted">
            {batch.created_by_name ?? "Another HR"} set this batch up. Only they or an admin can
            change who is in it.
          </p>
        )}
      </div>

      {addOpen && (
        <Dialog
          open
          onOpenChange={(o) => !o && setAddOpen(false)}
          title={`Add to ${batch.code}`}
          description="Your students who are not already in a batch."
        >
          <div className="flex max-h-80 flex-col gap-1 overflow-y-auto">
            {assignable.length === 0 && (
              <p className="px-1 py-6 text-center text-sm text-fg-muted">
                Everyone of yours is already in a batch.
              </p>
            )}
            {assignable.map((s) => (
              <button
                key={s.id}
                type="button"
                onClick={() => {
                  assign.mutate(s.id);
                  setAddOpen(false);
                }}
                className="flex items-center gap-2.5 rounded-md px-2 py-2 text-left transition-colors hover:bg-subtle"
              >
                <Avatar name={s.name} size="sm" />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-fg">{s.name}</p>
                  <p className="truncate text-xs text-fg-muted">
                    {s.domain} ·{" "}
                    {balanceOf(s) > 0 ? `${money(balanceOf(s))} pending` : "settled"}
                  </p>
                </div>
                <UserPlus className="size-4 text-fg-muted" aria-hidden />
              </button>
            ))}
          </div>
        </Dialog>
      )}
    </div>
  );
}
