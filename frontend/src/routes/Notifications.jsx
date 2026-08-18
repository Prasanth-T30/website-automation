import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, Bell, Info, TriangleAlert } from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { Card } from "@/components/ui/Card";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/States";
import { notificationsApi } from "@/features/notifications/api";
import { ApiError } from "@/lib/api";
import { dateTime } from "@/lib/format";
const META = {
  danger: { icon: AlertTriangle, tone: "bg-danger-subtle text-danger" },
  warning: { icon: TriangleAlert, tone: "bg-warn-subtle text-warn" },
  primary: { icon: Info, tone: "bg-brand-subtle text-brand" },
};
export default function Notifications() {
  const notifications = useQuery({ queryKey: ["notifications"], queryFn: notificationsApi.list });
  return (
    <>
      <PageHeader
        title="Notifications"
        description="Derived automatically from batch expiries and payment status — nothing here is stored."
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
              const meta = META[n.type];
              const Icon = meta.icon;
              return (
                <div key={n.id} className="flex gap-3 p-4">
                  <div
                    className={`flex size-9 shrink-0 items-center justify-center rounded-full ${meta.tone}`}
                  >
                    <Icon className="size-[18px]" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm font-semibold text-fg">{n.title}</p>
                    <p className="mt-0.5 text-xs text-fg-secondary">{n.description}</p>
                    {n.created_at && (
                      <p className="mt-1 text-[11px] text-fg-muted">{dateTime(n.created_at)}</p>
                    )}
                  </div>
                </div>
              );
            })}
          </Card>
        )}
      </div>
    </>
  );
}
