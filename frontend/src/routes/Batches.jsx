import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Layers, Plus, Users } from "lucide-react";
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
import { ApiError } from "@/lib/api";
import { shortDate } from "@/lib/format";
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
            {batches.data.map((b) => (
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
                    <Badge tone={TONE[b.status]} className="capitalize">
                      {b.status}
                    </Badge>
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
                      {b.created_by_name ? `Created by ${b.created_by_name}` : "Created by —"}
                    </span>
                    {!b.can_edit && (
                      <span className="shrink-0 text-[10px] font-bold tracking-wide text-fg-muted uppercase">
                        View only
                      </span>
                    )}
                  </div>
                </CardBody>
              </Card>
            ))}
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
  const roster = useQuery({
    queryKey: ["students", { batch_id: batch.id }],
    queryFn: () => studentsApi.list({ batch_id: batch.id }),
  });
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
            Roster {roster.data ? `(${roster.data.length})` : ""}
          </h3>
        </div>

        {roster.isPending && <LoadingState label="Loading roster…" />}

        {roster.data && (
          <ul className="divide-y divide-line-subtle rounded-md border border-line-subtle">
            {roster.data.map((s) => (
              <li key={s.id} className="flex items-center gap-2.5 px-3 py-2.5">
                <Avatar name={s.name} size="sm" />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-fg">{s.name}</p>
                  <p className="text-xs text-fg-muted">{s.email}</p>
                </div>
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
              </li>
            ))}
            {roster.data.length === 0 && (
              <li className="px-3 py-6 text-center text-xs text-fg-muted">No students yet.</li>
            )}
          </ul>
        )}
      </div>
    </div>
  );
}
