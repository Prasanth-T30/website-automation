import { Inbox, X } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { MockBanner } from "@/components/MockBanner";
import { PageHeader } from "@/components/PageHeader";
import { Avatar } from "@/components/ui/Avatar";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/States";
import { cn } from "@/lib/cn";
import { shortDate } from "@/lib/format";
import { MOCK_APPLICATIONS, hrName, type ApplicationStatus, type MockApplication } from "@/mock/data";

const TABS: { key: ApplicationStatus | "all"; label: string }[] = [
  { key: "new", label: "Unclaimed" },
  { key: "claimed", label: "Claimed" },
  { key: "converted", label: "Converted" },
  { key: "rejected", label: "Rejected" },
  { key: "all", label: "All" },
];

const TONE: Record<ApplicationStatus, "warn" | "brand" | "success" | "danger"> = {
  new: "warn",
  claimed: "brand",
  converted: "success",
  rejected: "danger",
};

export default function Applications() {
  const [apps, setApps] = useState<MockApplication[]>(MOCK_APPLICATIONS);
  const [tab, setTab] = useState<ApplicationStatus | "all">("new");

  const claim = (id: string) => {
    setApps((prev) =>
      prev.map((a) => (a.id === id ? { ...a, status: "claimed", claimed_by: "hr-1" } : a)),
    );
    toast.success("Claimed under your name.");
  };

  const reject = (id: string) => {
    setApps((prev) => prev.map((a) => (a.id === id ? { ...a, status: "rejected" } : a)));
    toast("Application rejected.");
  };

  const visible = apps.filter((a) => tab === "all" || a.status === tab);

  return (
    <>
      <PageHeader
        title="Applications"
        description="The same shared pool as the Pipeline board, in table form. Claim, review and reject from here."
      />
      <MockBanner phase="Phase 2 — Public intake, shared pool and claim" />

      <div className="p-6">
        <div className="mb-4 flex gap-1 overflow-x-auto">
          {TABS.map((t) => {
            const count = apps.filter((a) => t.key === "all" || a.status === t.key).length;
            return (
              <button
                key={t.key}
                onClick={() => setTab(t.key)}
                className={cn(
                  "flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-semibold whitespace-nowrap transition-colors",
                  tab === t.key
                    ? "bg-brand text-on-brand"
                    : "text-fg-secondary hover:bg-subtle",
                )}
              >
                {t.label}
                <span className={cn("text-[10px]", tab === t.key ? "opacity-80" : "text-fg-muted")}>
                  {count}
                </span>
              </button>
            );
          })}
        </div>

        <Card className="overflow-hidden">
          {visible.length === 0 ? (
            <EmptyState
              icon={<Inbox className="size-6" />}
              title="Nothing here"
              description="No applications match this filter."
            />
          ) : (
            <div className="scroll-x">
              <table className="w-full min-w-[820px] text-sm">
                <thead>
                  <tr className="border-b border-line-subtle bg-subtle/60 text-left">
                    {["Applicant", "College", "Domain", "Received", "Owner", "Status", ""].map((h) => (
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
                  {visible.map((a) => (
                    <tr key={a.id} className="border-b border-line-subtle last:border-0">
                      <td className="px-4 py-3">
                        <p className="font-medium text-fg">{a.full_name}</p>
                        <p className="text-xs text-fg-muted">{a.email} · {a.phone}</p>
                      </td>
                      <td className="px-4 py-3 text-fg-secondary">{a.college_name}</td>
                      <td className="px-4 py-3 text-fg-secondary">{a.domain_interest}</td>
                      <td className="px-4 py-3 text-xs text-fg-muted">{shortDate(a.created_at)}</td>
                      <td className="px-4 py-3">
                        {a.claimed_by ? (
                          <div className="flex items-center gap-1.5">
                            <Avatar name={hrName(a.claimed_by)} size="sm" />
                            <span className="text-xs text-fg-secondary">{hrName(a.claimed_by)}</span>
                          </div>
                        ) : (
                          <span className="text-xs text-fg-muted">—</span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <Badge tone={TONE[a.status]} className="capitalize">
                          {a.status}
                        </Badge>
                      </td>
                      <td className="px-4 py-3">
                        {a.status === "new" && (
                          <div className="flex justify-end gap-1">
                            <Button size="sm" onClick={() => claim(a.id)}>
                              Claim
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => reject(a.id)}
                              aria-label="Reject"
                            >
                              <X className="size-3.5" />
                            </Button>
                          </div>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>
    </>
  );
}
