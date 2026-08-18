import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Award, FileText, Receipt, Trash2, Upload } from "lucide-react";
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
import { studentsApi } from "@/features/students/api";
import { ApiError } from "@/lib/api";
import { cn } from "@/lib/cn";
import { shortDate } from "@/lib/format";
const CATEGORY_META = {
  certificate: { label: "Certificate", icon: Award, tone: "bg-success-subtle text-success" },
  call_letter: { label: "Call Letter", icon: FileText, tone: "bg-brand-subtle text-brand" },
  invoice: { label: "Invoice", icon: Receipt, tone: "bg-warn-subtle text-warn" },
  other: { label: "Other", icon: FileText, tone: "bg-subtle text-fg-muted" },
};
const TABS = [
  { key: "all", label: "All" },
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

      <div className="p-6 pt-4">
        {reports.isPending && <LoadingState label="Loading files…" />}

        {reports.isError && (
          <ErrorState
            description={
              reports.error instanceof ApiError ? reports.error.detail : "Could not load files."
            }
            onRetry={() => reports.refetch()}
          />
        )}

        {reports.data && visible.length === 0 && (
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
