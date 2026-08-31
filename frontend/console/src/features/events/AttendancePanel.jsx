import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CalendarDays, Check, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/States";
import { eventsApi } from "@/features/events/api";
import { shortDate } from "@/lib/format";

/**
 * The register for one day of a workshop or bootcamp.
 *
 * A day at a time, because that is how a register is actually taken — the
 * whole roster in one sitting, then saved once. Marking each person as you
 * tap them would put sixty round trips on a college's wifi.
 *
 * Unmarked is a real state, distinct from absent. Someone added to the roster
 * after a day was marked has no mark for it, and the count says so rather
 * than quietly reading as complete.
 */
export function AttendancePanel({ event, people }) {
  const queryClient = useQueryClient();
  const [day, setDay] = useState(null);
  // What is on screen but not yet saved, keyed by attendee id.
  const [draft, setDraft] = useState({});

  const days = useQuery({
    queryKey: ["events", event?.id, "days"],
    queryFn: () => eventsApi.days(event.id),
    enabled: Boolean(event?.id),
  });

  // Default to the first day the event ran, once we know what those are.
  useEffect(() => {
    if (!day && days.data?.length) setDay(days.data[0]);
  }, [day, days.data]);

  const register = useQuery({
    queryKey: ["events", event?.id, "attendance", day],
    queryFn: () => eventsApi.attendance(event.id, day),
    enabled: Boolean(event?.id && day),
  });

  // Saved marks, overlaid with anything changed since.
  const saved = useMemo(() => {
    const map = {};
    for (const mark of register.data?.marks ?? []) map[mark.attendee_id] = mark.status;
    return map;
  }, [register.data]);

  const statusOf = (id) => draft[id] ?? saved[id] ?? null;
  const dirty = Object.keys(draft).length > 0;

  const save = useMutation({
    mutationFn: () =>
      eventsApi.markAttendance(
        event.id,
        day,
        // Everyone on the roster, not just what changed: the register is for
        // a day as a whole, and leaving people out would file a half-marked
        // day that reads as partly unrecorded.
        people.map((person) => ({
          attendee_id: person.id,
          status: statusOf(person.id) ?? "absent",
        })),
      ),
    onSuccess: () => {
      setDraft({});
      queryClient.invalidateQueries({
        queryKey: ["events", event.id, "attendance", day],
      });
      toast.success(`Attendance saved for ${shortDate(day)}.`);
    },
    onError: () => toast.error("Could not save the register."),
  });

  const setAll = (status) =>
    setDraft(Object.fromEntries(people.map((person) => [person.id, status])));

  if (days.isLoading) return <LoadingState />;
  if (days.isError) return <ErrorState onRetry={days.refetch} />;
  if (people.length === 0) {
    return (
      <EmptyState
        icon={CalendarDays}
        title="Nobody to mark yet"
        description="Upload the register on the Attendees tab first."
      />
    );
  }

  const counts = register.data;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs font-semibold text-fg-muted">Day</span>
        {(days.data ?? []).map((value, index) => (
          <button
            key={value}
            type="button"
            onClick={() => {
              setDay(value);
              setDraft({});
            }}
            className={`h-8 rounded-md border px-3 text-xs font-semibold transition-colors ${
              value === day
                ? "border-brand bg-brand text-on-brand"
                : "border-line bg-surface text-fg-secondary hover:bg-subtle"
            }`}
          >
            Day {index + 1} · {shortDate(value)}
          </button>
        ))}
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <Button variant="secondary" size="sm" onClick={() => setAll("present")}>
          Mark all present
        </Button>
        <Button variant="secondary" size="sm" onClick={() => setAll("absent")}>
          Mark all absent
        </Button>
        {counts && (
          <span className="ml-auto flex items-center gap-2 text-xs font-semibold">
            <Badge tone="success">{counts.present} present</Badge>
            <Badge tone="danger">{counts.absent} absent</Badge>
            {counts.unmarked > 0 && (
              <Badge tone="warn">{counts.unmarked} unmarked</Badge>
            )}
          </span>
        )}
      </div>

      {register.isLoading && <LoadingState />}

      <div className="max-h-[38vh] overflow-y-auto rounded-md border border-line-subtle">
        <table className="w-full text-sm">
          <tbody>
            {people.map((person) => {
              const status = statusOf(person.id);
              return (
                <tr key={person.id} className="border-b border-line-subtle last:border-0">
                  <td className="px-3 py-2">
                    <p className="font-medium text-fg">{person.name}</p>
                    {person.department && (
                      <p className="text-xs text-fg-muted">
                        {person.department}
                        {person.year ? ` · ${person.year}` : ""}
                      </p>
                    )}
                  </td>
                  <td className="px-3 py-2 text-right">
                    {status === null && (
                      <span className="mr-2 text-xs font-semibold text-warn-text">
                        not marked
                      </span>
                    )}
                    <div className="inline-flex overflow-hidden rounded-md border border-line">
                      <button
                        type="button"
                        aria-label={`${person.name} present`}
                        onClick={() =>
                          setDraft((d) => ({ ...d, [person.id]: "present" }))
                        }
                        className={`flex h-8 w-10 items-center justify-center transition-colors ${
                          status === "present"
                            ? "bg-success text-on-success"
                            : "bg-surface text-fg-muted hover:bg-subtle"
                        }`}
                      >
                        <Check className="size-4" aria-hidden />
                      </button>
                      <button
                        type="button"
                        aria-label={`${person.name} absent`}
                        onClick={() =>
                          setDraft((d) => ({ ...d, [person.id]: "absent" }))
                        }
                        className={`flex h-8 w-10 items-center justify-center border-l border-line transition-colors ${
                          status === "absent"
                            ? "bg-danger text-on-danger"
                            : "bg-surface text-fg-muted hover:bg-subtle"
                        }`}
                      >
                        <X className="size-4" aria-hidden />
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-medium text-fg-muted">
          {dirty ? "Unsaved changes" : "Saved"}
        </span>
        <Button onClick={() => save.mutate()} disabled={!dirty || save.isPending}>
          {save.isPending ? "Saving…" : `Save ${day ? shortDate(day) : "day"}`}
        </Button>
      </div>
    </div>
  );
}
