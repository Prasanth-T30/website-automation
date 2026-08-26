import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FileSignature, Inbox, X } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";
import { PageHeader } from "@/components/PageHeader";
import { Avatar } from "@/components/ui/Avatar";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Dialog } from "@/components/ui/Dialog";
import { Field } from "@/components/ui/Field";
import { Pagination, usePagination } from "@/components/ui/Pagination";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/States";
import { applicationsApi } from "@/features/applications/api";
import { useAuth } from "@/features/auth/AuthProvider";
import { OfferLetterDialog } from "@/features/students/IssueDocumentDialog";
import { studentsApi } from "@/features/students/api";
import { usersApi } from "@/features/users/api";
import { ApiError } from "@/lib/api";
import { cn } from "@/lib/cn";
import { money, shortDate } from "@/lib/format";
const APPLICATIONS_KEY = ["applications"];
const EMAIL_ENABLED_CATEGORIES = new Set(["Internship", "Course"]);
const TABS = [
  { key: "pending", label: "Unclaimed" },
  { key: "claimed", label: "Claimed" },
  { key: "approved", label: "Approved" },
  { key: "rejected", label: "Rejected" },
  { key: "all", label: "All" },
];
const CATEGORY_TONE = {
  Internship: "brand",
  Course: "success",
  Project: "warn",
};
const STATUS_TONE = {
  pending: "warn",
  claimed: "brand",
  approved: "success",
  rejected: "danger",
};
const rejectSchema = z.object({
  reason: z.string().min(5, "Give at least a short reason.").max(1000),
});
const approveSchema = z.object({
  subject: z.string().max(200),
  body: z.string(),
  // The applicant only tells us what they are paying now. The course fee is
  // the HR's to state, and without it every student enrols already settled.
  total_fees: z.coerce
    .number({ invalid_type_error: "Enter the total course fee" })
    .min(0, "Fee cannot be negative"),
});
export default function Applications() {
  const { user, isAdmin } = useAuth();
  const queryClient = useQueryClient();
  const [tab, setTab] = useState("pending");
  const [approveTarget, setApproveTarget] = useState(null);
  const [rejectTarget, setRejectTarget] = useState(null);
  const [offerTarget, setOfferTarget] = useState(null);
  const applications = useQuery({
    queryKey: [...APPLICATIONS_KEY, tab],
    queryFn: () => applicationsApi.list(tab === "all" ? undefined : { status: tab }),
  });
  // Only to mark rows whose letter has already gone out. Shares Documents'
  // query key, so whichever screen loads first pays for it once. Skipped
  // entirely on tabs that show nothing approved.
  const offerCandidates = useQuery({
    queryKey: ["students", "offer-candidates"],
    queryFn: studentsApi.offerCandidates,
    enabled: (applications.data ?? []).some((a) => a.status === "approved"),
    staleTime: 60_000,
  });
  const issuedFor = new Set(
    (offerCandidates.data ?? []).filter((c) => c.already_issued).map((c) => c.id),
  );
  // Admin can resolve every HR's name for the owner column; an HR viewer only
  // ever needs to distinguish "mine" from "someone else's" (no /admin/users access).
  const allUsers = useQuery({
    queryKey: ["admin", "users"],
    queryFn: usersApi.list,
    enabled: isAdmin,
    staleTime: 5 * 60_000,
  });
  const ownerLabel = (ownerId) => {
    if (!ownerId) return "—";
    if (ownerId === user?.id) return "You";
    const match = allUsers.data?.find((u) => u.id === ownerId);
    return match?.full_name ?? "Another HR";
  };
  const invalidate = () =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey: APPLICATIONS_KEY }),
      queryClient.invalidateQueries({ queryKey: ["students", "offer-candidates"] }),
    ]);
  const claim = useMutation({
    mutationFn: (id) => applicationsApi.claim(id),
    onSuccess: async () => {
      await invalidate();
      toast.success("Claimed under your name.");
    },
    onError: (err) => toast.error(err instanceof ApiError ? err.detail : "Could not claim."),
  });
  const approve = useMutation({
    mutationFn: ({ id, values }) => applicationsApi.approve(id, values),
    onSuccess: async (updated) => {
      await invalidate();
      setApproveTarget(null);
      toast.success("Approved — the applicant is now a student.");
      // Sending the letter is the next thing this HR has to do, so open it
      // here rather than making them find the row again.
      if (updated?.converted_student_id) setOfferTarget(updated);
    },
    onError: (err) => toast.error(err instanceof ApiError ? err.detail : "Could not approve."),
  });
  const reject = useMutation({
    mutationFn: ({ id, reason }) => applicationsApi.reject(id, reason),
    onSuccess: async () => {
      await invalidate();
      setRejectTarget(null);
      toast("Application rejected.");
    },
    onError: (err) => toast.error(err instanceof ApiError ? err.detail : "Could not reject."),
  });
  const rows = applications.data ?? [];
  const paging = usePagination(rows);
  return (
    <>
      <PageHeader
        title="Applications"
        description="Every registration from the public form lands here. Claim one to take it under your name, then approve or reject."
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
        <Card className="overflow-hidden">
          {applications.isPending && <LoadingState label="Loading applications…" />}

          {applications.isError && (
            <ErrorState
              description={
                applications.error instanceof ApiError
                  ? applications.error.detail
                  : "Could not load applications."
              }
              onRetry={() => applications.refetch()}
            />
          )}

          {applications.data && rows.length === 0 && (
            <EmptyState
              icon={<Inbox className="size-6" />}
              title="Nothing here"
              description="No applications match this filter."
            />
          )}

          {rows.length > 0 && (
            <div className="scroll-x">
              <table className="w-full min-w-[900px] text-sm">
                <thead>
                  <tr className="border-b border-line-subtle bg-subtle/60 text-left">
                    {[
                      "Applicant",
                      "College",
                      "Category / Domain",
                      "Amount",
                      "Received",
                      "Owner",
                      "Status",
                      "",
                    ].map((h) => (
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
                  {paging.pageItems.map((a) => {
                    const isMineOrAdmin = isAdmin || a.owner_id === user?.id;
                    const canAct =
                      a.status === "pending" ||
                      ((a.status === "claimed" || a.status === "approved") && isMineOrAdmin);
                    return (
                      <tr key={a.id} className="border-b border-line-subtle last:border-0">
                        <td className="px-4 py-3">
                          <p className="font-medium text-fg">
                            {a.title ? `${a.title} ` : ""}
                            {a.name}
                          </p>
                          <p className="text-xs text-fg-muted">
                            {a.email} · {a.phone}
                          </p>
                          <p className="mt-0.5 font-mono text-[11px] text-fg-muted">
                            {a.registration_id}
                          </p>
                        </td>
                        <td className="px-4 py-3 text-fg-secondary">
                          {a.college}
                          {/* Where they are from and when they finish — the two
                              things an HR asks about on a first call, so they
                              belong next to the college rather than a click
                              away. `place` is where they live now; `native` is
                              the home district, and they are usually different. */}
                          {(a.native_place || a.passed_out_year) && (
                            <p className="mt-0.5 text-xs text-fg-muted">
                              {[
                                a.native_place && `Native: ${a.native_place}`,
                                a.passed_out_year && `Passing out ${a.passed_out_year}`,
                              ]
                                .filter(Boolean)
                                .join(" · ")}
                            </p>
                          )}
                        </td>
                        <td className="px-4 py-3">
                          <Badge tone={CATEGORY_TONE[a.category] ?? "brand"}>{a.category}</Badge>
                          <p className="mt-1 text-xs text-fg-secondary">
                            {a.domain} · {a.duration}
                            {a.mode ? ` · ${a.mode}` : ""}
                          </p>
                          {a.project_topic && (
                            <p className="mt-1 text-xs text-fg-muted">Topic: {a.project_topic}</p>
                          )}
                          {/* Whatever the applicant typed under "Other". Shown
                              in full rather than truncated — it is the one place
                              they can say something the form didn't ask for. */}
                          {a.other && (
                            <p className="mt-1.5 max-w-[28ch] rounded-md border-l-2 border-accent bg-subtle px-2 py-1 text-xs break-words text-fg-secondary">
                              <span className="font-semibold text-fg-muted">Other: </span>
                              {a.other}
                            </p>
                          )}
                        </td>
                        <td className="px-4 py-3 font-semibold text-fg">{money(a.amount)}</td>
                        <td className="px-4 py-3 text-xs text-fg-muted">
                          {a.created_at ? shortDate(a.created_at) : "—"}
                        </td>
                        <td className="px-4 py-3">
                          {a.owner_id ? (
                            <div className="flex items-center gap-1.5">
                              <Avatar name={ownerLabel(a.owner_id)} size="sm" />
                              <span className="text-xs text-fg-secondary">
                                {ownerLabel(a.owner_id)}
                              </span>
                            </div>
                          ) : (
                            <span className="text-xs text-fg-muted">—</span>
                          )}
                        </td>
                        <td className="px-4 py-3">
                          <Badge tone={STATUS_TONE[a.status]} className="capitalize">
                            {a.status}
                          </Badge>
                        </td>
                        <td className="px-4 py-3">
                          {canAct && (
                            <div className="flex justify-end gap-1">
                              {a.status === "pending" && (
                                <Button
                                  size="sm"
                                  loading={claim.isPending}
                                  onClick={() => claim.mutate(a.id)}
                                >
                                  Claim
                                </Button>
                              )}
                              {a.status === "claimed" && (
                                <>
                                  <Button size="sm" onClick={() => setApproveTarget(a)}>
                                    Approve
                                  </Button>
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => setRejectTarget(a)}
                                    aria-label="Reject"
                                  >
                                    <X className="size-3.5" />
                                  </Button>
                                </>
                              )}
                              {a.status === "approved" &&
                                (a.converted_student_id ? (
                                  <>
                                    {issuedFor.has(a.converted_student_id) && (
                                      <Badge tone="success">Sent</Badge>
                                    )}
                                    <Button
                                      size="sm"
                                      variant="secondary"
                                      onClick={() => setOfferTarget(a)}
                                    >
                                      <FileSignature className="size-3.5" aria-hidden /> Generate
                                    </Button>
                                  </>
                                ) : (
                                  /* Approved before enrolment started recording
                                     a student id — there is nobody to send a
                                     letter for, so offer the PDF alone. */
                                  <a
                                    href={applicationsApi.offerLetterUrl(a.id)}
                                    target="_blank"
                                    rel="noreferrer"
                                    className="text-xs font-semibold text-[var(--brand-text)] hover:underline"
                                  >
                                    Offer letter
                                  </a>
                                ))}
                            </div>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          {rows.length > 0 && <Pagination {...paging} label="applications" />}
        </Card>
      </div>

      {approveTarget && (
        <ApproveDialog
          application={approveTarget}
          onClose={() => setApproveTarget(null)}
          onSubmit={(values) => approve.mutate({ id: approveTarget.id, values })}
          loading={approve.isPending}
        />
      )}

      {offerTarget?.converted_student_id && (
        <OfferLetterDialog
          studentId={offerTarget.converted_student_id}
          name={offerTarget.name}
          email={offerTarget.email}
          alreadyIssued={issuedFor.has(offerTarget.converted_student_id)}
          onClose={() => setOfferTarget(null)}
        />
      )}

      <Dialog
        open={rejectTarget !== null}
        onOpenChange={(o) => !o && setRejectTarget(null)}
        title="Reject this application?"
        description="The applicant is notified by email with the reason you give."
      >
        {rejectTarget && (
          <RejectForm
            onSubmit={(values) => reject.mutate({ id: rejectTarget.id, reason: values.reason })}
            onCancel={() => setRejectTarget(null)}
            loading={reject.isPending}
          />
        )}
      </Dialog>
    </>
  );
}
function ApproveDialog({ application, onClose, onSubmit, loading }) {
  const sendsEmail = EMAIL_ENABLED_CATEGORIES.has(application.category);
  const paid = application.amount || 0;
  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(approveSchema),
    defaultValues: {
      subject: `${application.category} Offer Letter — DVein Innovations`,
      body: "",
      total_fees: paid,
    },
  });

  const total = Number(watch("total_fees"));
  const pending = Number.isFinite(total) ? Math.max(0, total - paid) : 0;
  return (
    <Dialog
      open
      onOpenChange={(o) => !o && onClose()}
      title="Approve application"
      description={
        sendsEmail
          ? "Enrols the applicant as a student. The offer letter is generated and sent in the next step, once you have seen it."
          : "Project registrations don't send an email — this just confirms enrollment."
      }
    >
      <form onSubmit={handleSubmit(onSubmit)} noValidate className="flex flex-col gap-4">
        {/* Fees. Approving is the moment the real course fee is known, and the
            only chance to set it before the student reaches Finance. */}
        <div className="rounded-lg border border-line bg-subtle p-4">
          <Field
            label="Total course fee"
            error={errors.total_fees?.message}
            hint="What this student owes in total. Their registration payment counts towards it."
            required
          >
            <input
              type="number"
              min="0"
              step="1"
              autoFocus
              className="h-10 w-full rounded-md border border-line bg-surface px-3 text-sm text-fg"
              {...register("total_fees")}
            />
          </Field>
          <dl className="mt-3 grid grid-cols-2 gap-2 text-sm">
            <dt className="text-fg-muted">Already paid</dt>
            <dd className="text-right font-medium tabular-nums text-fg">{money(paid)}</dd>
            <dt className="text-fg-muted">Pending</dt>
            <dd
              className={`text-right font-semibold tabular-nums ${
                pending > 0 ? "text-warn-text" : "text-success-text"
              }`}
            >
              {money(pending)}
            </dd>
          </dl>
        </div>

        {sendsEmail && (
          <>
            <Field label="Subject" error={errors.subject?.message}>
              <input
                className="h-10 w-full rounded-md border border-line bg-surface px-3 text-sm text-fg"
                {...register("subject")}
              />
            </Field>
            <Field label="Message" hint="Leave blank to use the standard template.">
              <textarea
                rows={5}
                className="w-full rounded-md border border-line bg-surface px-3 py-2 text-sm text-fg"
                {...register("body")}
              />
            </Field>
          </>
        )}
        <div className="mt-2 flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={loading}>
            Approve
          </Button>
        </div>
      </form>
    </Dialog>
  );
}
function RejectForm({ onSubmit, onCancel, loading }) {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm({ resolver: zodResolver(rejectSchema) });
  return (
    <form onSubmit={handleSubmit(onSubmit)} noValidate className="flex flex-col gap-4">
      <Field label="Reason" error={errors.reason?.message} required>
        <textarea
          rows={4}
          autoFocus
          className="w-full rounded-md border border-line bg-surface px-3 py-2 text-sm text-fg"
          {...register("reason")}
        />
      </Field>
      <div className="flex justify-end gap-2">
        <Button type="button" variant="secondary" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" variant="danger" loading={loading}>
          Reject
        </Button>
      </div>
    </form>
  );
}
