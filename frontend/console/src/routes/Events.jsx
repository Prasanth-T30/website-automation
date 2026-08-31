import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Banknote,
  CalendarRange,
  GraduationCap,
  Lock,
  Pencil,
  Plus,
  Trash2,
  Users,
  Wallet,
} from "lucide-react";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import { PageHeader } from "@/components/PageHeader";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardBody } from "@/components/ui/Card";
import { Dialog } from "@/components/ui/Dialog";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/States";
import { eventsApi } from "@/features/events/api";
import { RosterDialog } from "@/features/events/RosterDialog";
import { money, shortDate } from "@/lib/format";

/**
 * Off-campus revenue: work run at a college rather than sold to an individual.
 *
 * These never pass through applications, students or the fee ledger, so there
 * is nothing to derive them from — every row is typed in by the HR who ran the
 * event. They are also the one money surface in this console that is private:
 * what you record here, only you can see.
 */

// Order matters — it is the order the sections appear in, and it runs from
// the shortest engagement to the longest.
const EVENT_TYPES = [
  { value: "workshop", label: "Workshop" },
  { value: "bootcamp", label: "Bootcamp" },
  { value: "training_program", label: "Training Program" },
  { value: "addon_course", label: "Add-on Course" },
  { value: "industrial_visit", label: "Industrial Visit" },
];

const LABELS = Object.fromEntries(EVENT_TYPES.map((t) => [t.value, t.label]));

// Which events carry a named register. Workshops and bootcamps are attended
// by a list of students the college sends; the rest are booked as a block.
const ROSTER_KINDS = new Set(["workshop", "bootcamp"]);

// `Input` here is a bare <input>, so a dropdown is a real <select> carrying
// the same shape by hand — the same thing the filter bars on Payments do.
const selectClass =
  "h-10 w-full rounded-md border border-line bg-surface px-3 text-sm text-fg transition-colors focus:border-brand";

const BLANK = {
  event_type: "workshop",
  college: "",
  student_count: "",
  amount_collected: "",
  amount_receivable: "",
  start_date: "",
  end_date: "",
  days_conducted: "",
  notes: "",
};

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

/** Record or correct one event. The same form does both. */
function EventDialog({ open, onOpenChange, initial, onSubmit, saving }) {
  const [form, setForm] = useState(BLANK);
  const [errors, setErrors] = useState({});
  // Reset when the dialog is opened for a different row, rather than in an
  // effect that would fight the user's typing.
  const [openedFor, setOpenedFor] = useState(null);
  const key = initial?.id ?? "new";
  if (open && openedFor !== key) {
    setOpenedFor(key);
    setForm(
      initial
        ? {
            event_type: initial.event_type,
            college: initial.college,
            student_count: String(initial.student_count ?? ""),
            amount_collected: String(initial.amount_collected ?? ""),
            amount_receivable: String(initial.amount_receivable ?? ""),
            start_date: initial.start_date ?? "",
            end_date: initial.end_date ?? "",
            days_conducted: String(initial.days_conducted ?? ""),
            notes: initial.notes ?? "",
          }
        : BLANK,
    );
    setErrors({});
  }

  const set = (field) => (e) => setForm((f) => ({ ...f, [field]: e.target.value }));

  const submit = (e) => {
    e.preventDefault();
    const found = {};
    if (form.college.trim().length < 2) found.college = "Name the college.";
    if (!form.start_date) found.start_date = "When did it start?";
    if (!form.end_date) found.end_date = "When did it end?";
    if (form.start_date && form.end_date && form.end_date < form.start_date) {
      found.end_date = "It cannot end before it starts.";
    }
    setErrors(found);
    if (Object.keys(found).length > 0) return;

    onSubmit({
      event_type: form.event_type,
      college: form.college.trim(),
      // Blank means none, not invalid — a free workshop and one with nobody
      // still owing are both ordinary.
      student_count: Number(form.student_count || 0),
      amount_collected: Number(form.amount_collected || 0),
      amount_receivable: Number(form.amount_receivable || 0),
      start_date: form.start_date,
      end_date: form.end_date,
      days_conducted: Number(form.days_conducted || 0),
      notes: form.notes.trim() || null,
    });
  };

  return (
    <Dialog
      open={open}
      onOpenChange={onOpenChange}
      title={initial ? "Edit event" : "Record an event"}
      description="Only you can see what you record here."
      footer={
        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button form="event-form" type="submit" disabled={saving}>
            {saving ? "Saving…" : initial ? "Save changes" : "Record event"}
          </Button>
        </div>
      }
    >
      <form id="event-form" onSubmit={submit} className="grid grid-cols-2 gap-4">
        <Field label="Event type" required className="col-span-2">
          <select value={form.event_type} onChange={set("event_type")} className={selectClass}>
            {EVENT_TYPES.map((t) => (
              <option key={t.value} value={t.value}>
                {t.label}
              </option>
            ))}
          </select>
        </Field>

        <Field label="College" required error={errors.college} className="col-span-2">
          <Input
            value={form.college}
            onChange={set("college")}
            placeholder="Where it was held"
          />
        </Field>

        <Field label="Number of students">
          <Input type="number" min="0" value={form.student_count} onChange={set("student_count")} />
        </Field>
        <Field
          label="Days conducted"
          hint="Days it actually ran, not the span."
        >
          <Input
            type="number"
            min="0"
            value={form.days_conducted}
            onChange={set("days_conducted")}
          />
        </Field>

        <Field label="Amount collected (Rs.)">
          <Input
            type="number"
            min="0"
            step="0.01"
            value={form.amount_collected}
            onChange={set("amount_collected")}
          />
        </Field>
        <Field label="Amount to receive (Rs.)">
          <Input
            type="number"
            min="0"
            step="0.01"
            value={form.amount_receivable}
            onChange={set("amount_receivable")}
          />
        </Field>

        <Field label="Start date" required error={errors.start_date}>
          <Input type="date" value={form.start_date} onChange={set("start_date")} />
        </Field>
        <Field label="End date" required error={errors.end_date}>
          <Input type="date" value={form.end_date} onChange={set("end_date")} />
        </Field>

        <Field label="Notes" className="col-span-2">
          <Input value={form.notes} onChange={set("notes")} placeholder="Optional" />
        </Field>
      </form>
    </Dialog>
  );
}

function EventRow({ event, onEdit, onDelete, onRoster }) {
  return (
    <div className="flex flex-wrap items-center gap-3 border-t border-line-subtle px-4 py-3 first:border-t-0">
      <div className="min-w-[12rem] flex-1">
        <p className="text-sm font-bold text-fg">{event.college}</p>
        <p className="mt-0.5 text-xs text-fg-muted">
          {shortDate(event.start_date)} – {shortDate(event.end_date)}
          {" · "}
          {event.days_conducted} {event.days_conducted === 1 ? "day" : "days"} conducted
        </p>
        {event.notes && <p className="mt-1 text-xs text-fg-secondary">{event.notes}</p>}
      </div>

      <div className="text-right">
        <p className="text-xs font-semibold text-fg-muted">Students</p>
        <p className="text-sm font-bold text-fg">{event.student_count}</p>
      </div>
      <div className="w-28 text-right">
        <p className="text-xs font-semibold text-fg-muted">Collected</p>
        <p className="text-sm font-bold text-fg">{money(event.amount_collected)}</p>
      </div>
      <div className="w-28 text-right">
        <p className="text-xs font-semibold text-fg-muted">To receive</p>
        <p
          className={`text-sm font-bold ${
            event.amount_receivable > 0 ? "text-warn-text" : "text-fg-muted"
          }`}
        >
          {money(event.amount_receivable)}
        </p>
      </div>

      <div className="flex items-center gap-1">
        {/* Only the two kinds of event that bring a register with them. A
            training programme or an industrial visit is booked as a block,
            not attended by a named list. */}
        {ROSTER_KINDS.has(event.event_type) && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onRoster(event)}
            aria-label={`Attendees for ${event.college}`}
          >
            <Users className="size-4" aria-hidden />
          </Button>
        )}
        <Button variant="ghost" size="sm" onClick={() => onEdit(event)} aria-label="Edit event">
          <Pencil className="size-4" aria-hidden />
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => onDelete(event)}
          aria-label="Delete event"
        >
          <Trash2 className="size-4 text-danger-text" aria-hidden />
        </Button>
      </div>
    </div>
  );
}

export default function Events() {
  const queryClient = useQueryClient();
  const [dialogFor, setDialogFor] = useState(null); // null | {} | event
  const [confirmDelete, setConfirmDelete] = useState(null);
  const [rosterFor, setRosterFor] = useState(null);

  const list = useQuery({ queryKey: ["events"], queryFn: () => eventsApi.list() });
  const summary = useQuery({ queryKey: ["events", "summary"], queryFn: eventsApi.summary });

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ["events"] });
    // The admin performance report folds this money into the HR's total.
    queryClient.invalidateQueries({ queryKey: ["hr-performance"] });
  };

  const save = useMutation({
    mutationFn: (data) =>
      dialogFor?.id ? eventsApi.update(dialogFor.id, data) : eventsApi.create(data),
    onSuccess: () => {
      toast.success(dialogFor?.id ? "Event updated" : "Event recorded");
      setDialogFor(null);
      refresh();
    },
    onError: (err) => toast.error(err.message || "Could not save the event"),
  });

  const remove = useMutation({
    mutationFn: (id) => eventsApi.remove(id),
    onSuccess: () => {
      toast.success("Event deleted");
      setConfirmDelete(null);
      refresh();
    },
    onError: (err) => toast.error(err.message || "Could not delete the event"),
  });

  // Grouped into a section per kind, in the fixed order above, so the page
  // reads the same every time rather than reshuffling as rows are added.
  const sections = useMemo(() => {
    const rows = list.data ?? [];
    return EVENT_TYPES.map((type) => ({
      ...type,
      rows: rows.filter((e) => e.event_type === type.value),
    }));
  }, [list.data]);

  const totals = summary.data;

  return (
    <>
      <PageHeader
        title="Events"
        description="Workshops, bootcamps, training programmes, add-on courses and industrial visits you have run."
        action={
          <Button onClick={() => setDialogFor({})}>
            <Plus className="size-4" aria-hidden /> Record event
          </Button>
        }
      />

      <div className="mb-4 flex items-center gap-2 rounded-md border border-line-subtle bg-subtle px-3 py-2 text-xs font-medium text-fg-secondary">
        <Lock className="size-3.5 shrink-0" aria-hidden />
        Private to you. Colleagues cannot see these events; the money counts
        toward your own revenue total.
      </div>

      <div className="mb-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <StatTile
          icon={CalendarRange}
          label="Events recorded"
          value={totals ? totals.event_count : "—"}
          tone="bg-brand-subtle text-brand"
        />
        <StatTile
          icon={GraduationCap}
          label="Students reached"
          value={totals ? totals.student_count : "—"}
          tone="bg-subtle text-fg-secondary"
        />
        <StatTile
          icon={Banknote}
          label="Collected"
          value={totals ? money(totals.amount_collected) : "—"}
          tone="bg-success-subtle text-success"
        />
        <StatTile
          icon={Wallet}
          label="Still to receive"
          value={totals ? money(totals.amount_receivable) : "—"}
          tone="bg-warn-subtle text-warn"
        />
      </div>

      {list.isLoading && <LoadingState />}
      {list.isError && <ErrorState onRetry={list.refetch} />}

      {list.isSuccess && (list.data ?? []).length === 0 && (
        <EmptyState
          title="No events recorded yet"
          description="Record a workshop, bootcamp, training programme, add-on course or industrial visit you have run."
          action={
            <Button onClick={() => setDialogFor({})}>
              <Plus className="size-4" aria-hidden /> Record event
            </Button>
          }
        />
      )}

      {list.isSuccess && (list.data ?? []).length > 0 && (
        <div className="flex flex-col gap-5">
          {sections
            // A kind you have never run is noise, not information.
            .filter((section) => section.rows.length > 0)
            .map((section) => {
              const collected = section.rows.reduce((sum, e) => sum + e.amount_collected, 0);
              return (
                <section key={section.value}>
                  <div className="mb-2 flex items-center gap-2">
                    <h2 className="text-sm font-extrabold text-fg">{section.label}</h2>
                    <Badge tone="neutral">{section.rows.length}</Badge>
                    <span className="ml-auto text-xs font-semibold text-fg-muted">
                      {money(collected)} collected
                    </span>
                  </div>
                  <Card className="overflow-hidden">
                    {section.rows.map((event) => (
                      <EventRow
                        key={event.id}
                        event={event}
                        onEdit={setDialogFor}
                        onDelete={setConfirmDelete}
                        onRoster={setRosterFor}
                      />
                    ))}
                  </Card>
                </section>
              );
            })}
        </div>
      )}

      <RosterDialog
        event={rosterFor}
        open={rosterFor !== null}
        onOpenChange={(next) => !next && setRosterFor(null)}
      />

      <EventDialog
        open={dialogFor !== null}
        onOpenChange={(next) => !next && setDialogFor(null)}
        initial={dialogFor?.id ? dialogFor : null}
        onSubmit={save.mutate}
        saving={save.isPending}
      />

      <Dialog
        open={confirmDelete !== null}
        onOpenChange={(next) => !next && setConfirmDelete(null)}
        title="Delete this event?"
        description={
          confirmDelete
            ? `${LABELS[confirmDelete.event_type]} at ${confirmDelete.college}. Its ${money(
                confirmDelete.amount_collected,
              )} comes back out of your revenue total.`
            : ""
        }
        footer={
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setConfirmDelete(null)}>
              Cancel
            </Button>
            <Button
              variant="danger"
              disabled={remove.isPending}
              onClick={() => remove.mutate(confirmDelete.id)}
            >
              {remove.isPending ? "Deleting…" : "Delete event"}
            </Button>
          </div>
        }
      />
    </>
  );
}
