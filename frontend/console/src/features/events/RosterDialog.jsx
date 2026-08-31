import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Download, Trash2, Upload, Users } from "lucide-react";
import { useRef, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/States";
import { eventsApi } from "@/features/events/api";
import { ApiError } from "@/lib/api";

/**
 * Who attended one workshop or bootcamp.
 *
 * These are deliberately not students. A student is an enrolment — fees, a
 * batch, a duration, a place in the certificate pipeline — and a workshop
 * attendee has none of that. They live in their own collection on the server
 * and never reach the Students page, so importing a college's register of
 * sixty names cannot distort the fee ledger or the dashboard counts.
 */
export function RosterDialog({ event, open, onOpenChange }) {
  const queryClient = useQueryClient();
  const fileInput = useRef(null);
  const [lastImport, setLastImport] = useState(null);

  const roster = useQuery({
    queryKey: ["events", event?.id, "attendees"],
    queryFn: () => eventsApi.attendees(event.id),
    enabled: Boolean(open && event?.id),
  });

  const refresh = () =>
    queryClient.invalidateQueries({ queryKey: ["events", event?.id, "attendees"] });

  const importFile = useMutation({
    mutationFn: (file) => eventsApi.importAttendees(event.id, file),
    onSuccess: (result) => {
      setLastImport(result);
      refresh();
      toast.success(
        `Added ${result.imported} ${result.imported === 1 ? "person" : "people"}.`,
      );
    },
    onError: (err) =>
      toast.error(err instanceof ApiError ? err.detail : "Could not read that file."),
    // The picker keeps the chosen filename, so re-selecting the same
    // corrected file would otherwise not fire a change event.
    onSettled: () => {
      if (fileInput.current) fileInput.current.value = "";
    },
  });

  const removeOne = useMutation({
    mutationFn: (attendeeId) => eventsApi.removeAttendee(event.id, attendeeId),
    onSuccess: refresh,
    onError: () => toast.error("Could not remove that person."),
  });

  const clearAll = useMutation({
    mutationFn: () => eventsApi.clearRoster(event.id),
    onSuccess: () => {
      setLastImport(null);
      refresh();
      toast.success("Roster cleared.");
    },
    onError: () => toast.error("Could not clear the roster."),
  });

  const people = roster.data ?? [];

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next) setLastImport(null);
        onOpenChange(next);
      }}
      title={event ? `Attendees — ${event.college}` : "Attendees"}
      description="Upload the college's register. These stay on this event and never join your student list."
      className="max-w-3xl"
      footer={
        <div className="flex items-center justify-between gap-2">
          <span className="text-xs font-semibold text-fg-muted">
            {people.length} on the roster
            {event?.student_count ? ` · ${event.student_count} recorded on the event` : ""}
          </span>
          <div className="flex gap-2">
            {people.length > 0 && (
              <Button
                variant="ghost"
                onClick={() => clearAll.mutate()}
                disabled={clearAll.isPending}
              >
                Clear roster
              </Button>
            )}
            <Button variant="secondary" onClick={() => onOpenChange(false)}>
              Done
            </Button>
          </div>
        </div>
      }
    >
      <div className="flex flex-col gap-4">
        <div className="rounded-md border border-dashed border-line bg-subtle p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-sm font-bold text-fg">Upload a register</p>
              <p className="mt-0.5 text-xs text-fg-muted">
                Excel or CSV, with a <strong>Name</strong> column. Email, phone,
                department and year are picked up when present. Download the
                template if you want the exact format.
              </p>
            </div>
            <input
              ref={fileInput}
              type="file"
              accept=".xlsx,.xlsm,.csv"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) importFile.mutate(file);
              }}
            />
            <div className="flex items-center gap-2">
              {/* A plain link, not a fetch: the browser handles the download
                  and the session cookie rides along. */}
              <a
                href={eventsApi.templateUrl()}
                className="inline-flex h-10 items-center gap-2 rounded-md border border-line bg-surface px-4 text-sm font-semibold text-fg transition-colors hover:bg-subtle"
              >
                <Download className="size-4" aria-hidden /> Template
              </a>
              <Button
                onClick={() => fileInput.current?.click()}
                disabled={importFile.isPending}
              >
                <Upload className="size-4" aria-hidden />
                {importFile.isPending ? "Reading…" : "Choose file"}
              </Button>
            </div>
          </div>

          {/* Rows the file had that could not be used. Shown in full rather
              than as a count, so a partial import can be corrected instead
              of guessed at. */}
          {lastImport?.skipped?.length > 0 && (
            <div className="mt-3 rounded-md border border-warn-subtle bg-warn-subtle px-3 py-2">
              <p className="text-xs font-bold text-warn-text">
                {lastImport.skipped.length} row
                {lastImport.skipped.length === 1 ? "" : "s"} skipped
              </p>
              <ul className="mt-1 list-disc pl-4 text-xs text-warn-text">
                {lastImport.skipped.slice(0, 8).map((line) => (
                  <li key={line}>{line}</li>
                ))}
                {lastImport.skipped.length > 8 && (
                  <li>…and {lastImport.skipped.length - 8} more</li>
                )}
              </ul>
            </div>
          )}
        </div>

        {roster.isLoading && <LoadingState />}
        {roster.isError && <ErrorState onRetry={roster.refetch} />}

        {roster.isSuccess && people.length === 0 && (
          <EmptyState
            icon={Users}
            title="Nobody on the roster yet"
            description="Upload the register the college sent and the names will appear here."
          />
        )}

        {people.length > 0 && (
          <div className="scroll-x max-h-[45vh] overflow-y-auto rounded-md border border-line-subtle">
            <table className="w-full min-w-[560px] text-sm">
              <thead className="sticky top-0 bg-subtle">
                <tr className="border-b border-line-subtle text-left">
                  {["Name", "Email", "Phone", "Department", "Year", ""].map((h) => (
                    <th
                      key={h}
                      className="px-3 py-2 text-xs font-bold tracking-wide text-fg-muted uppercase"
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {people.map((person) => (
                  <tr key={person.id} className="border-b border-line-subtle last:border-0">
                    <td className="px-3 py-2 font-medium text-fg">{person.name}</td>
                    <td className="px-3 py-2 text-fg-secondary">{person.email ?? "—"}</td>
                    <td className="px-3 py-2 text-fg-secondary">{person.phone ?? "—"}</td>
                    <td className="px-3 py-2 text-fg-secondary">
                      {person.department ?? "—"}
                    </td>
                    <td className="px-3 py-2 text-fg-secondary">{person.year ?? "—"}</td>
                    <td className="px-3 py-2 text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        aria-label={`Remove ${person.name}`}
                        onClick={() => removeOne.mutate(person.id)}
                      >
                        <Trash2 className="size-4 text-danger-text" aria-hidden />
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </Dialog>
  );
}
