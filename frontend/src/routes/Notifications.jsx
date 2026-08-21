import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, Bell, Info, Megaphone, Trash2, TriangleAlert } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Dialog } from "@/components/ui/Dialog";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/States";
import { announcementsApi } from "@/features/announcements/api";
import { useAuth } from "@/features/auth/AuthProvider";
import { notificationsApi } from "@/features/notifications/api";
import { ApiError } from "@/lib/api";
import { dateTime } from "@/lib/format";

const META = {
  danger: { icon: AlertTriangle, tone: "bg-danger-subtle text-danger" },
  warning: { icon: TriangleAlert, tone: "bg-warn-subtle text-warn" },
  primary: { icon: Info, tone: "bg-brand-subtle text-brand" },
};

/** Announcements carry a stable id prefix, so the feed can tell one from a
 *  derived alert without adding a field to every notification. */
const isAnnouncement = (id) => typeof id === "string" && id.startsWith("announcement-");
const announcementIdOf = (id) => id.replace(/^announcement-/, "");

export default function Notifications() {
  const { isAdmin } = useAuth();
  const queryClient = useQueryClient();
  const [composeOpen, setComposeOpen] = useState(false);

  const notifications = useQuery({ queryKey: ["notifications"], queryFn: notificationsApi.list });

  const remove = useMutation({
    mutationFn: (id) => announcementsApi.remove(id),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["notifications"] });
      toast.success("Announcement removed.");
    },
    onError: (err) => toast.error(err instanceof ApiError ? err.detail : "Could not remove it."),
  });

  return (
    <>
      <PageHeader
        title="Notifications"
        description={
          isAdmin
            ? "Batch expiries and payment alerts, derived automatically — plus anything you announce to the team."
            : "Batch expiries, payment alerts, and announcements from your administrator."
        }
        action={
          isAdmin ? (
            <Button onClick={() => setComposeOpen(true)}>
              <Megaphone className="size-4" aria-hidden /> Announce
            </Button>
          ) : null
        }
      />

      <div className="mx-auto max-w-2xl p-6">
        {notifications.isPending && <LoadingState label="Loading notifications…" />}

        {notifications.isError && (
          <ErrorState
            description={
              notifications.error instanceof ApiError
                ? notifications.error.detail
                : "Could not load notifications."
            }
            onRetry={() => notifications.refetch()}
          />
        )}

        {notifications.data && notifications.data.length === 0 && (
          <Card>
            <EmptyState
              icon={<Bell className="size-6" />}
              title="All clear"
              description="No alerts right now."
            />
          </Card>
        )}

        {notifications.data && notifications.data.length > 0 && (
          <Card className="divide-y divide-line-subtle overflow-hidden">
            {notifications.data.map((n) => {
              const announced = isAnnouncement(n.id);
              const meta = META[n.type] ?? META.primary;
              const Icon = announced ? Megaphone : meta.icon;
              return (
                <div
                  key={n.id}
                  className={`flex gap-3 p-4 ${announced ? "bg-brand-subtle/25" : ""}`}
                >
                  <div
                    className={`flex size-9 shrink-0 items-center justify-center rounded-full ${meta.tone}`}
                  >
                    <Icon className="size-[18px]" />
                  </div>
                  <div className="min-w-0 flex-1">
                    {announced && (
                      <p className="text-[10px] font-bold tracking-wide text-fg-muted uppercase">
                        Announcement
                      </p>
                    )}
                    <p className="text-sm font-semibold text-fg">{n.title}</p>
                    {n.description && (
                      <p className="mt-0.5 text-xs whitespace-pre-line text-fg-secondary">
                        {n.description}
                      </p>
                    )}
                    {n.created_at && (
                      <p className="mt-1 text-[11px] text-fg-muted">{dateTime(n.created_at)}</p>
                    )}
                  </div>
                  {/* Only an announcement can be taken down. The rest are
                      recomputed from live data and would simply come back. */}
                  {announced && isAdmin && (
                    <button
                      type="button"
                      onClick={() => remove.mutate(announcementIdOf(n.id))}
                      disabled={remove.isPending}
                      aria-label={`Remove announcement: ${n.title}`}
                      className="h-fit rounded p-1 text-fg-muted transition-colors hover:bg-danger-subtle hover:text-danger"
                    >
                      <Trash2 className="size-4" aria-hidden />
                    </button>
                  )}
                </div>
              );
            })}
          </Card>
        )}
      </div>

      {composeOpen && <ComposeAnnouncement onClose={() => setComposeOpen(false)} />}
    </>
  );
}

function ComposeAnnouncement({ onClose }) {
  const queryClient = useQueryClient();
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [level, setLevel] = useState("primary");
  const [expiresAt, setExpiresAt] = useState("");

  const post = useMutation({
    mutationFn: () =>
      announcementsApi.create({
        title: title.trim(),
        body: body.trim(),
        level,
        // A date input gives a local calendar day. Send the end of it, so a
        // notice set to expire "today" stays up for the whole of today.
        expires_at: expiresAt ? new Date(`${expiresAt}T23:59:59`).toISOString() : null,
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["notifications"] });
      onClose();
      toast.success("Announced to the whole team.");
    },
    onError: (err) =>
      toast.error(err instanceof ApiError ? err.detail : "Could not post the announcement."),
  });

  return (
    <Dialog
      open
      onOpenChange={(o) => !o && onClose()}
      title="Announce to the team"
      description="Every HR sees this at the top of their notifications."
    >
      <div className="flex flex-col gap-4">
        <Field label="Title" required>
          <Input
            autoFocus
            maxLength={120}
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. Office closed on Friday"
          />
        </Field>

        <Field label="Message" hint="Optional. Line breaks are kept.">
          <textarea
            rows={4}
            maxLength={2000}
            value={body}
            onChange={(e) => setBody(e.target.value)}
            className="w-full rounded-md border border-line bg-surface px-3 py-2 text-sm text-fg"
            placeholder="Anything the team needs to know."
          />
        </Field>

        <div className="grid grid-cols-2 gap-3">
          <Field label="Importance">
            <select
              value={level}
              onChange={(e) => setLevel(e.target.value)}
              className="h-10 w-full rounded-md border border-line bg-surface px-3 text-sm text-fg"
            >
              <option value="primary">Normal</option>
              <option value="warning">Important</option>
              <option value="danger">Urgent</option>
            </select>
          </Field>
          <Field label="Remove after" hint="Optional.">
            <Input type="date" value={expiresAt} onChange={(e) => setExpiresAt(e.target.value)} />
          </Field>
        </div>

        <div className="mt-2 flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button
            onClick={() => post.mutate()}
            loading={post.isPending}
            disabled={title.trim().length < 3}
          >
            Announce
          </Button>
        </div>
      </div>
    </Dialog>
  );
}
