import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Award,
  FileSignature,
  FileText,
  Receipt,
  Search,
  Send,
  Trash2,
  Upload,
} from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { PageHeader } from "@/components/PageHeader";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardBody } from "@/components/ui/Card";
import { Dialog } from "@/components/ui/Dialog";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/States";
import { useAuth } from "@/features/auth/AuthProvider";
import { reportsApi } from "@/features/reports/api";
import { CertificateDialog, OfferLetterDialog } from "@/features/students/IssueDocumentDialog";
import { studentsApi } from "@/features/students/api";
import { ApiError } from "@/lib/api";
import { cn } from "@/lib/cn";
import { money, shortDate } from "@/lib/format";
const CATEGORY_META = {
  offer_letter: { label: "Offer Letter", icon: FileSignature, tone: "bg-brand-subtle text-brand" },
  certificate: { label: "Certificate", icon: Award, tone: "bg-success-subtle text-success" },
  call_letter: { label: "Call Letter", icon: FileText, tone: "bg-brand-subtle text-brand" },
  invoice: { label: "Invoice", icon: Receipt, tone: "bg-warn-subtle text-warn" },
  other: { label: "Other", icon: FileText, tone: "bg-subtle text-fg-muted" },
};
const TABS = [
  { key: "all", label: "All" },
  // Not filters like the others: these two tabs are where the document is
  // generated and sent, so they lead.
  { key: "offer_letter", label: "Offer Letters" },
  { key: "certificate", label: "Certificates" },
  { key: "call_letter", label: "Call Letters" },
  { key: "invoice", label: "Invoices" },
  { key: "other", label: "Other" },
];
const REPORTS_KEY = ["reports"];
function formatSize(bytes) {
  return bytes > 1_000_000
    ? `${(bytes / 1_000_000).toFixed(1)} MB`
    : `${Math.round(bytes / 1000)} KB`;
}
export default function Reports() {
  const { user, isAdmin } = useAuth();
  const [tab, setTab] = useState("all");
  const [uploadOpen, setUploadOpen] = useState(false);
  const queryClient = useQueryClient();
  const reports = useQuery({ queryKey: REPORTS_KEY, queryFn: () => reportsApi.list() });
  const students = useQuery({ queryKey: ["students"], queryFn: () => studentsApi.list() });
  const studentName = (id) => (id ? (students.data?.find((s) => s.id === id)?.name ?? id) : null);
  const remove = useMutation({
    mutationFn: reportsApi.remove,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: REPORTS_KEY });
      toast.success("File deleted.");
    },
    onError: (err) => toast.error(err instanceof ApiError ? err.detail : "Could not delete file."),
  });
  const visible = (reports.data ?? []).filter((r) => tab === "all" || r.category === tab);
  return (
    <>
      <PageHeader
        title="Certificates & Reports"
        description="Files uploaded against students or the institute — call letters, certificates, invoices."
        action={
          <Button onClick={() => setUploadOpen(true)}>
            <Upload className="size-4" /> Upload file
          </Button>
        }
      />

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

      <div className="flex flex-col gap-4 p-6 pt-4">
        {/* The offer-letter tab does two jobs: it sends new letters, and
            below that it lists the ones already filed. */}
        {tab === "offer_letter" && <OfferLetterPanel />}
        {tab === "certificate" && <CertificateLookup />}
        {tab === "certificate" && <CertificatePanel />}

        {reports.isPending && <LoadingState label="Loading files…" />}

        {reports.isError && (
          <ErrorState
            description={
              reports.error instanceof ApiError ? reports.error.detail : "Could not load files."
            }
            onRetry={() => reports.refetch()}
          />
        )}

        {reports.data && visible.length === 0 && tab !== "offer_letter" && tab !== "certificate" && (
          <Card>
            <EmptyState icon={<FileText className="size-6" />} title="No files in this category" />
          </Card>
        )}

        {visible.length > 0 && (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {visible.map((r) => {
              const meta = CATEGORY_META[r.category];
              const Icon = meta.icon;
              const canDelete = isAdmin || r.uploaded_by_id === user?.id;
              const linkedName = studentName(r.student_id);
              return (
                <Card key={r.id}>
                  <CardBody className="flex flex-col gap-3">
                    <div className="flex items-start justify-between gap-2">
                      <div
                        className={`flex size-9 items-center justify-center rounded-md ${meta.tone}`}
                      >
                        <Icon className="size-[18px]" />
                      </div>
                      <div className="flex items-center gap-1.5">
                        <Badge tone="neutral">{meta.label}</Badge>
                        {canDelete && (
                          <button
                            onClick={() => remove.mutate(r.id)}
                            disabled={remove.isPending}
                            className="text-fg-muted transition-colors hover:text-danger-text"
                            aria-label="Delete file"
                          >
                            <Trash2 className="size-3.5" />
                          </button>
                        )}
                      </div>
                    </div>
                    <a
                      href={reportsApi.downloadUrl(r.id)}
                      className="text-sm font-semibold text-fg hover:text-[var(--brand-text)] hover:underline"
                    >
                      {r.title}
                    </a>
                    {linkedName && <p className="text-xs text-fg-muted">{linkedName}</p>}
                    <div className="flex items-center justify-between text-xs text-fg-muted">
                      <span>{formatSize(r.file_size_bytes)}</span>
                      <span>{r.created_at ? shortDate(r.created_at) : "—"}</span>
                    </div>
                  </CardBody>
                </Card>
              );
            })}
          </div>
        )}
      </div>

      <UploadDialog open={uploadOpen} onOpenChange={setUploadOpen} students={students.data ?? []} />
    </>
  );
}
function UploadDialog({ open, onOpenChange, students }) {
  const queryClient = useQueryClient();
  const [title, setTitle] = useState("");
  const [category, setCategory] = useState("certificate");
  const [studentId, setStudentId] = useState("");
  const [file, setFile] = useState(null);
  const reset = () => {
    setTitle("");
    setCategory("certificate");
    setStudentId("");
    setFile(null);
  };
  const upload = useMutation({
    mutationFn: () =>
      reportsApi.upload({ title, category, student_id: studentId || undefined, file: file }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: REPORTS_KEY });
      onOpenChange(false);
      reset();
      toast.success("File uploaded.");
    },
    onError: (err) => toast.error(err instanceof ApiError ? err.detail : "Could not upload file."),
  });
  return (
    <Dialog
      open={open}
      onOpenChange={(o) => {
        if (!o) reset();
        onOpenChange(o);
      }}
      title="Upload a file"
      description="Certificates, call letters, invoices, or other institute documents."
    >
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (title && file) upload.mutate();
        }}
        className="flex flex-col gap-4"
      >
        <Field label="Title" required>
          <Input autoFocus value={title} onChange={(e) => setTitle(e.target.value)} />
        </Field>
        <Field label="Category" required>
          <select
            className="h-10 w-full rounded-md border border-line bg-surface px-3 text-sm text-fg"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
          >
            {Object.entries(CATEGORY_META).map(([value, meta]) => (
              <option key={value} value={value}>
                {meta.label}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Student" hint="Leave blank for institute-wide documents.">
          <select
            className="h-10 w-full rounded-md border border-line bg-surface px-3 text-sm text-fg"
            value={studentId}
            onChange={(e) => setStudentId(e.target.value)}
          >
            <option value="">— None —</option>
            {students.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </Field>
        <Field label="File" required>
          <input
            type="file"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="text-sm text-fg file:mr-3 file:rounded-md file:border-0 file:bg-subtle file:px-3 file:py-1.5 file:text-xs file:font-semibold"
          />
        </Field>
        <div className="mt-2 flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button type="submit" loading={upload.isPending} disabled={!title || !file}>
            Upload
          </Button>
        </div>
      </form>
    </Dialog>
  );
}

/**
 * Send an offer letter, without leaving Documents.
 *
 * The review-and-send half lives in OfferLetterDialog, which Applications
 * opens too — one letter, one way of sending it.
 */
/**
 * Issue a certificate, without leaving Documents.
 *
 * Unlike offer letters, eligibility is a date rather than a payment: a
 * student appears here as their programme reaches its last few days, so the
 * certificate is ready when they finish rather than whenever someone
 * remembers. The review-and-send half is the shared dialog.
 */
/**
 * Check a certificate number someone has been handed.
 *
 * The number is printed under every certificate, and this is where a call
 * that starts "is this real?" gets answered. Any signed-in member of staff
 * can use it, not only the student's own HR — a check nobody is available
 * for is no check at all.
 *
 * It reports two things separately, because they are not the same: whether
 * the number matches a student, and whether a certificate was actually
 * issued to them. The number is derived from the student's record id, so it
 * is computable for anyone ever enrolled — a match alone proves nothing.
 */
function CertificateLookup() {
  const [number, setNumber] = useState("");
  const [submitted, setSubmitted] = useState("");

  const result = useQuery({
    queryKey: ["certificate-lookup", submitted],
    queryFn: () => studentsApi.certificateLookup(submitted),
    enabled: submitted.length > 0,
    retry: false,
  });

  const found = result.data;

  return (
    <Card>
      <CardBody className="flex flex-col gap-3">
        <div>
          <h3 className="text-sm font-bold text-fg">Check a certificate</h3>
          <p className="mt-0.5 text-xs text-fg-muted">
            Paste the number printed under a certificate to see who it was issued to.
          </p>
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            setSubmitted(number.trim().toUpperCase());
          }}
          className="flex flex-wrap items-center gap-2"
        >
          <Input
            value={number}
            onChange={(e) => setNumber(e.target.value)}
            placeholder="DVN-CERT-7F3A91C2"
            className="max-w-xs font-mono"
            aria-label="Certificate number"
          />
          <Button type="submit" variant="secondary" disabled={!number.trim()}>
            <Search className="size-3.5" aria-hidden /> Check
          </Button>
        </form>

        {result.isFetching && <LoadingState label="Checking…" />}

        {result.isError && (
          <p className="rounded-md border border-danger/30 bg-danger-subtle px-3 py-2 text-xs text-danger-text">
            {result.error instanceof ApiError
              ? result.error.detail
              : "Could not check that number."}
          </p>
        )}

        {found && !found.student_found && (
          <p className="rounded-md border border-danger/30 bg-danger-subtle px-3 py-2 text-xs text-danger-text">
            <strong className="font-mono">{found.certificate_number}</strong> does not match any
            student. Treat the document as unverified.
          </p>
        )}

        {found?.student_found && (
          <div
            className={cn(
              "rounded-md border p-3",
              found.issued
                ? "border-success/30 bg-success-subtle"
                : "border-warn/30 bg-warn-subtle",
            )}
          >
            <p
              className={cn(
                "text-xs font-bold",
                found.issued ? "text-success-text" : "text-warn-text",
              )}
            >
              {found.issued
                ? "Genuine — a certificate was issued for this number."
                : "This number matches a student, but no certificate has been issued to them."}
            </p>

            <dl className="mt-2.5 grid grid-cols-2 gap-x-4 gap-y-1.5 text-xs">
              {[
                ["Name", found.name],
                ["College", found.college],
                ["Programme", [found.domain, found.category].filter(Boolean).join(" · ")],
                ["Duration", found.duration],
                ["Enrolment", found.status],
                [
                  "Issued",
                  found.issued_on
                    ? shortDate(found.issued_on) +
                      (found.issued_count > 1 ? ` · ${found.issued_count} copies` : "")
                    : "—",
                ],
              ].map(([label, value]) => (
                <div key={label} className="contents">
                  <dt className="text-fg-muted">{label}</dt>
                  <dd className="font-medium text-fg capitalize">{value || "—"}</dd>
                </div>
              ))}
            </dl>
          </div>
        )}
      </CardBody>
    </Card>
  );
}

function CertificatePanel() {
  const [selected, setSelected] = useState(null);
  const [query, setQuery] = useState("");

  const candidates = useQuery({
    queryKey: ["students", "certificate-candidates"],
    queryFn: () => studentsApi.certificateCandidates(),
  });

  const rows = (candidates.data ?? []).filter((c) =>
    !query.trim() ? true : c.name.toLowerCase().includes(query.trim().toLowerCase()),
  );

  /** "Ends in 3 days", "Ended 2 days ago", "Completed" — why they are here. */
  const dueLabel = (c) => {
    if (c.days_remaining === null || c.days_remaining === undefined) {
      return c.status === "completed" ? "Marked completed" : "No end date";
    }
    if (c.days_remaining > 1) return `Ends in ${c.days_remaining} days`;
    if (c.days_remaining === 1) return "Ends tomorrow";
    if (c.days_remaining === 0) return "Ends today";
    if (c.days_remaining === -1) return "Ended yesterday";
    return `Ended ${Math.abs(c.days_remaining)} days ago`;
  };

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardBody className="flex flex-col gap-3">
          <div>
            <h3 className="text-sm font-bold text-fg">Issue a certificate</h3>
            <p className="mt-0.5 text-xs text-fg-muted">
              Students appear here in the last five days of their programme, and stay until the
              certificate is sent. It goes to the email address on their registration.
            </p>
          </div>

          <Input
            placeholder="Search a student…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="max-w-xs"
          />

          {candidates.isPending && <LoadingState label="Loading students…" />}

          {candidates.isError && (
            <ErrorState
              description={
                candidates.error instanceof ApiError
                  ? candidates.error.detail
                  : "Could not load students."
              }
              onRetry={() => candidates.refetch()}
            />
          )}

          {candidates.data && rows.length === 0 && (
            <EmptyState
              icon={<Award className="size-6" />}
              title="Nobody is due yet"
              description="A student appears here once their programme is within five days of ending."
            />
          )}

          {rows.length > 0 && (
            <ul className="divide-y divide-line-subtle rounded-md border border-line-subtle">
              {rows.map((c) => (
                <li key={c.id} className="flex items-center gap-3 px-3 py-2.5">
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-fg">{c.name}</p>
                    <p className="truncate text-xs text-fg-muted">
                      {c.domain} · {c.duration}
                      {c.end_date ? ` · ends ${shortDate(c.end_date)}` : ""}
                    </p>
                  </div>
                  <Badge tone={c.days_remaining !== null && c.days_remaining < 0 ? "warn" : "brand"}>
                    {dueLabel(c)}
                  </Badge>
                  {c.already_issued && <Badge tone="success">Sent</Badge>}
                  <Button size="sm" variant="secondary" onClick={() => setSelected(c)}>
                    <Award className="size-3.5" aria-hidden /> Generate
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </CardBody>
      </Card>

      {selected && (
        <CertificateDialog
          studentId={selected.id}
          name={selected.name}
          email={selected.email}
          alreadyIssued={selected.already_issued}
          onClose={() => setSelected(null)}
        />
      )}
    </div>
  );
}

function OfferLetterPanel() {
  const [selected, setSelected] = useState(null);
  const [query, setQuery] = useState("");

  const candidates = useQuery({
    queryKey: ["students", "offer-candidates"],
    queryFn: studentsApi.offerCandidates,
  });

  const rows = (candidates.data ?? []).filter((c) =>
    !query.trim() ? true : c.name.toLowerCase().includes(query.trim().toLowerCase()),
  );

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardBody className="flex flex-col gap-3">
          <div>
            <h3 className="text-sm font-bold text-fg">Send an offer letter</h3>
            <p className="mt-0.5 text-xs text-fg-muted">
              Students who have paid appear here. The letter takes their name, domain and dates
              from what they submitted, and goes to the email address on their registration.
            </p>
          </div>

          <Input
            placeholder="Search a student…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="max-w-xs"
          />

          {candidates.isPending && <LoadingState label="Loading students…" />}

          {candidates.data && rows.length === 0 && (
            <EmptyState
              icon={<Send className="size-6" />}
              title="Nobody is eligible yet"
              description="A student appears here once a payment has been recorded against them."
            />
          )}

          {rows.length > 0 && (
            <ul className="divide-y divide-line-subtle rounded-md border border-line-subtle">
              {rows.map((c) => (
                <li key={c.id} className="flex items-center gap-3 px-3 py-2.5">
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-fg">{c.name}</p>
                    <p className="truncate text-xs text-fg-muted">
                      {c.domain} · {c.duration} · paid {money(c.fees_paid)}
                      {c.balance > 0 ? ` of ${money(c.total_fees)}` : " — settled"}
                    </p>
                  </div>
                  {c.already_issued && <Badge tone="success">Sent</Badge>}
                  <Button size="sm" variant="secondary" onClick={() => setSelected(c)}>
                    <FileSignature className="size-3.5" aria-hidden /> Generate
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </CardBody>
      </Card>

      {selected && (
        <OfferLetterDialog
          studentId={selected.id}
          name={selected.name}
          email={selected.email}
          alreadyIssued={selected.already_issued}
          onClose={() => setSelected(null)}
        />
      )}
    </div>
  );
}
