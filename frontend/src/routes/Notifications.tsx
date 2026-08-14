import { AlertTriangle, Bell, Info, TriangleAlert } from "lucide-react";

import { MockBanner } from "@/components/MockBanner";
import { PageHeader } from "@/components/PageHeader";
import { Card } from "@/components/ui/Card";
import { dateTime } from "@/lib/format";
import { MOCK_NOTIFICATIONS, type MockNotification } from "@/mock/data";

const META: Record<MockNotification["type"], { icon: typeof Bell; tone: string }> = {
  danger: { icon: AlertTriangle, tone: "bg-danger-subtle text-danger" },
  warning: { icon: TriangleAlert, tone: "bg-warn-subtle text-warn" },
  primary: { icon: Info, tone: "bg-brand-subtle text-brand" },
};

export default function Notifications() {
  const sorted = [...MOCK_NOTIFICATIONS].sort((a, b) => a.urgency - b.urgency);

  return (
    <>
      <PageHeader
        title="Notifications"
        description="Derived automatically from batch expiries and payment status — nothing here is stored."
      />
      <MockBanner phase="Phase 5 — Files, certificates and notifications" />

      <div className="mx-auto max-w-2xl p-6">
        <Card className="divide-y divide-line-subtle overflow-hidden">
          {sorted.map((n) => {
            const meta = META[n.type];
            const Icon = meta.icon;
            return (
              <div key={n.id} className="flex gap-3 p-4">
                <div className={`flex size-9 shrink-0 items-center justify-center rounded-full ${meta.tone}`}>
                  <Icon className="size-[18px]" />
                </div>
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-fg">{n.title}</p>
                  <p className="mt-0.5 text-xs text-fg-secondary">{n.desc}</p>
                  <p className="mt-1 text-[11px] text-fg-muted">{dateTime(n.created_at)}</p>
                </div>
              </div>
            );
          })}
        </Card>
      </div>
    </>
  );
}
