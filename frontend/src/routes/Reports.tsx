import { Award, FileText, Receipt, Upload } from "lucide-react";
import { useState } from "react";

import { MockBanner } from "@/components/MockBanner";
import { PageHeader } from "@/components/PageHeader";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardBody } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/States";
import { cn } from "@/lib/cn";
import { shortDate } from "@/lib/format";
import { MOCK_REPORTS, studentName, type MockReport, type ReportCategory } from "@/mock/data";

const CATEGORY_META: Record<ReportCategory, { label: string; icon: typeof Award; tone: string }> = {
  certificate: { label: "Certificate", icon: Award, tone: "bg-success-subtle text-success" },
  call_letter: { label: "Call Letter", icon: FileText, tone: "bg-brand-subtle text-brand" },
  invoice: { label: "Invoice", icon: Receipt, tone: "bg-warn-subtle text-warn" },
  other: { label: "Other", icon: FileText, tone: "bg-subtle text-fg-muted" },
};

const TABS: { key: ReportCategory | "all"; label: string }[] = [
  { key: "all", label: "All" },
  { key: "certificate", label: "Certificates" },
  { key: "call_letter", label: "Call Letters" },
  { key: "invoice", label: "Invoices" },
  { key: "other", label: "Other" },
];

function formatSize(bytes: number) {
  return bytes > 1_000_000 ? `${(bytes / 1_000_000).toFixed(1)} MB` : `${Math.round(bytes / 1000)} KB`;
}

export default function Reports() {
  const [tab, setTab] = useState<ReportCategory | "all">("all");
  const visible = MOCK_REPORTS.filter((r) => tab === "all" || r.category === tab);

  return (
    <>
      <PageHeader
        title="Certificates & Reports"
        description="Files uploaded against students or the institute — call letters, certificates, invoices."
        action={
          <Button>
            <Upload className="size-4" /> Upload file
          </Button>
        }
      />
      <MockBanner phase="Phase 5 — Files, certificates and notifications" />

      <div className="flex gap-1 overflow-x-auto px-6 pt-4">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={cn(
              "rounded-md px-3 py-1.5 text-xs font-semibold whitespace-nowrap transition-colors",
              tab === t.key ? "bg-brand text-on-brand" : "text-fg-secondary hover:bg-subtle",
            )}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="p-6 pt-4">
        {visible.length === 0 ? (
          <Card>
            <EmptyState icon={<FileText className="size-6" />} title="No files in this category" />
          </Card>
        ) : (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {visible.map((r: MockReport) => {
              const meta = CATEGORY_META[r.category];
              const Icon = meta.icon;
              return (
                <Card key={r.id}>
                  <CardBody className="flex flex-col gap-3">
                    <div className="flex items-start justify-between gap-2">
                      <div className={`flex size-9 items-center justify-center rounded-md ${meta.tone}`}>
                        <Icon className="size-[18px]" />
                      </div>
                      <Badge tone="neutral">{meta.label}</Badge>
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-fg">{r.title}</p>
                      {r.student_id && (
                        <p className="mt-0.5 text-xs text-fg-muted">{studentName(r.student_id)}</p>
                      )}
                    </div>
                    <div className="flex items-center justify-between text-xs text-fg-muted">
                      <span>{formatSize(r.file_size_bytes)}</span>
                      <span>{shortDate(r.uploaded_at)}</span>
                    </div>
                  </CardBody>
                </Card>
              );
            })}
          </div>
        )}
      </div>
    </>
  );
}
