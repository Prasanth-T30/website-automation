import { AlertTriangle, Banknote, CheckCircle2, Clock, Download } from "lucide-react";
import { useState } from "react";

import { MockBanner } from "@/components/MockBanner";
import { PageHeader } from "@/components/PageHeader";
import { Badge } from "@/components/ui/Badge";
import { Card, CardBody } from "@/components/ui/Card";
import { Dialog } from "@/components/ui/Dialog";
import { money, shortDate } from "@/lib/format";
import { MOCK_TRANSACTIONS, paymentsSummary, studentName, type MockTransaction } from "@/mock/data";

const MODE_TONE = { cash: "neutral", upi: "brand", bank: "success", cheque: "warn" } as const;

function StatTile({
  icon: Icon,
  label,
  value,
  tone,
}: {
  icon: typeof Banknote;
  label: string;
  value: string;
  tone: string;
}) {
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

export default function Payments() {
  const summary = paymentsSummary();
  const [receipt, setReceipt] = useState<MockTransaction | null>(null);

  return (
    <>
      <PageHeader
        title="Payments"
        description="Every recorded transaction, newest first. Receipts are illustrative — nothing here downloads a real PDF yet."
      />
      <MockBanner phase="Phase 4 — Payments, receipts and exports" />

      <div className="grid grid-cols-1 gap-4 p-6 sm:grid-cols-2 lg:grid-cols-4">
        <StatTile icon={Banknote} label="Total Revenue" value={money(summary.total_revenue)} tone="bg-success-subtle text-success" />
        <StatTile icon={Clock} label="Pending" value={money(summary.pending_amount)} tone="bg-warn-subtle text-warn" />
        <StatTile icon={AlertTriangle} label="Overdue" value={money(summary.overdue_amount)} tone="bg-danger-subtle text-danger" />
        <StatTile icon={CheckCircle2} label="Fully Paid" value={`${summary.paid_count} students`} tone="bg-brand-subtle text-brand" />
      </div>

      <div className="px-6 pb-6">
        <Card className="overflow-hidden">
          <div className="scroll-x">
            <table className="w-full min-w-[760px] text-sm">
              <thead>
                <tr className="border-b border-line-subtle bg-subtle/60 text-left">
                  {["Receipt", "Student", "Amount", "Mode", "Balance After", "Date", ""].map((h) => (
                    <th key={h} className="px-4 py-2.5 text-xs font-bold tracking-wide text-fg-muted uppercase">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {MOCK_TRANSACTIONS.slice(0, 30).map((t) => (
                  <tr key={t.id} className="border-b border-line-subtle last:border-0">
                    <td className="px-4 py-3 font-mono text-xs text-fg-secondary">{t.receipt_number}</td>
                    <td className="px-4 py-3 font-medium text-fg">{studentName(t.student_id)}</td>
                    <td className="px-4 py-3 font-semibold text-fg">{money(t.amount)}</td>
                    <td className="px-4 py-3">
                      <Badge tone={MODE_TONE[t.mode]} className="uppercase">{t.mode}</Badge>
                    </td>
                    <td className="px-4 py-3 text-fg-secondary">{money(t.balance_after)}</td>
                    <td className="px-4 py-3 text-xs text-fg-muted">{shortDate(t.paid_at)}</td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() => setReceipt(t)}
                        className="flex items-center gap-1 text-xs font-semibold text-[var(--brand-text)] hover:underline"
                      >
                        <Download className="size-3.5" /> Receipt
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </div>

      <Dialog
        open={receipt !== null}
        onOpenChange={(o) => !o && setReceipt(null)}
        title="Payment Receipt"
        description="Preview only — the real PDF export lands with Phase 4."
      >
        {receipt && (
          <div className="rounded-md border border-line bg-subtle/40 p-5 text-center">
            <p className="brand-gradient-text text-lg font-extrabold">Dvein Innovations</p>
            <p className="mt-0.5 text-xs text-fg-muted">Payment Receipt</p>
            <p className="mt-4 text-3xl font-extrabold text-fg">{money(receipt.amount)}</p>
            <div className="mt-4 space-y-1.5 text-left text-sm">
              {[
                ["Receipt No.", receipt.receipt_number],
                ["Student", studentName(receipt.student_id)],
                ["Date", shortDate(receipt.paid_at)],
                ["Mode", receipt.mode.toUpperCase()],
                ["Balance After", money(receipt.balance_after)],
              ].map(([label, value]) => (
                <div key={label} className="flex justify-between border-b border-line-subtle py-1.5">
                  <span className="text-fg-muted">{label}</span>
                  <span className="font-medium text-fg">{value}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </Dialog>
    </>
  );
}
