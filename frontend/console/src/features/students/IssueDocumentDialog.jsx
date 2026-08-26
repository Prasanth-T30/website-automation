import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Download, ExternalLink, Pencil, RotateCcw, Send } from "lucide-react";
import { lazy, Suspense, useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { LoadingState } from "@/components/ui/States";
import { publicApi } from "@/features/public/api";
import { studentsApi } from "@/features/students/api";
import { ApiError } from "@/lib/api";

/**
 * The two documents this dialog issues.
 *
 * They differ only in which endpoints they call and which fields reach the
 * page — the offer letter names a programme and its dates, the certificate
 * only ever prints a name and what was completed. Everything else about
 * reviewing, editing and sending is identical, and is deliberately shared so
 * the two cannot drift into behaving differently.
 */
export const OFFER_LETTER = {
  noun: "Offer letter",
  filePrefix: "Offer_Letter",
  candidatesKey: ["students", "offer-candidates"],
  draft: studentsApi.offerLetterDraft,
  preview: studentsApi.offerLetterPreview,
  issue: studentsApi.issueOfferLetter,
  fields: [
    { key: "salutation", label: "Salutation", choices: "titles" },
    { key: "name", label: "Name" },
    { key: "college", label: "College" },
    { key: "place", label: "Place" },
    { key: "category", label: "Category", choices: "categories" },
    { key: "domain", label: "Domain", choices: "domains" },
    { key: "duration", label: "Duration", choices: "durations" },
    { key: "start_date", label: "Start date" },
    { key: "end_date", label: "End date" },
  ],
};

export const CERTIFICATE = {
  noun: "Certificate",
  filePrefix: "Certificate",
  candidatesKey: ["students", "certificate-candidates"],
  draft: studentsApi.certificateDraft,
  preview: studentsApi.certificatePreview,
  issue: studentsApi.issueCertificate,
  // The certificate design carries no dates: it states what was completed,
  // not how long it took. Only these three reach the page.
  fields: [
    { key: "name", label: "Name" },
    { key: "category", label: "Category", choices: "categories" },
    { key: "domain", label: "Domain", choices: "domains" },
    // Who signs the right-hand rule. A domain may be taught by several
    // mentors, so this is picked rather than derived — the list is merely
    // ordered by domain.
    { key: "mentor_id", label: "Signed by", mentors: true },
  ],
};

/* pdf.js is ~450 KB and only matters once someone opens a document, so it is
   fetched then rather than carried on every page load of the console. */
const PdfPreview = lazy(() =>
  import("@/components/ui/PdfPreview").then((m) => ({ default: m.PdfPreview })),
);

const selectClass = "h-10 w-full rounded-md border border-line bg-surface px-3 text-sm text-fg";

/** Blank strings mean "leave it as the record has it", not "print nothing". */
function cleaned(fields) {
  return Object.fromEntries(
    Object.entries(fields ?? {}).filter(([, v]) => v !== null && v !== undefined && v !== ""),
  );
}

/**
 * The choice list, with the record's own value folded in when it predates it.
 *
 * Durations were once written "3 Months" where the form now offers "90 Days".
 * Without this the dropdown would quietly show blank for those students and
 * drop the value off their document.
 */
function withCurrent(options, current) {
  const list = options ?? [];
  return current && !list.includes(current) ? [current, ...list] : list;
}

function draftFrom(source) {
  return { subject: source.subject, body: source.body, fields: cleaned(source.fields) };
}

/**
 * Review, edit, then send a student document.
 *
 * Three steps on purpose: the PDF is rendered and shown, the HR may correct
 * anything on it or rewrite the covering email, and only then does Send mail
 * that exact file. Every preview goes through the same endpoint the send
 * does, edits included, so what is on screen is what arrives.
 *
 * Edits apply to this document alone. They are deliberately not written back
 * to the student record: fixing a spelling on one certificate should not
 * silently rewrite the enrolment it came from.
 *
 * @param {object} props
 * @param {OFFER_LETTER | CERTIFICATE} props.kind  Which document to issue.
 * @param {string} props.studentId  The enrolled student, not the application.
 * @param {string} props.name
 * @param {string} props.email  Where it goes, shown before sending.
 * @param {boolean} [props.alreadyIssued]  One is already filed for them.
 * @param {() => void} props.onClose
 */
export function IssueDocumentDialog({
  kind,
  studentId,
  name,
  email,
  alreadyIssued = false,
  onClose,
}) {
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState(false);
  /** Null until the draft lands, so an empty form can never be sent. */
  const [draft, setDraft] = useState(null);

  const source = useQuery({
    queryKey: ["students", studentId, kind.noun, "draft"],
    queryFn: () => kind.draft(studentId),
    staleTime: Infinity,
    // The client polls every 30s by default so three HRs sharing one pool
    // never work from a stale list. A document being reviewed is the
    // opposite case: it must sit still while it is read.
    refetchInterval: false,
    refetchOnWindowFocus: false,
  });

  // Selects rather than free text wherever the API only accepts a known
  // value, so an edit cannot produce a document the server will refuse.
  const choices = useQuery({
    queryKey: ["public", "choices"],
    queryFn: publicApi.choices,
    enabled: editing,
    staleTime: 5 * 60_000,
  });

  useEffect(() => {
    if (source.data && draft === null) setDraft(draftFrom(source.data));
  }, [source.data, draft]);

  /* Only the certificate has a signatory, and only while it is being edited.
     Ordered by the domain currently on the document, so changing the domain
     re-sorts who is offered. */
  const wantsMentors = kind.fields.some((f) => f.mentors);
  const mentors = useQuery({
    queryKey: ["students", "certificate-mentors", draft?.fields?.domain ?? null],
    queryFn: () => studentsApi.certificateMentors(draft?.fields?.domain),
    enabled: editing && wantsMentors,
    staleTime: 5 * 60_000,
  });

  /* The preview re-renders only when the document's own fields change:
     retyping the email body must not cost a PDF round trip. */
  const fieldsKey = JSON.stringify(draft?.fields ?? null);
  const preview = useQuery({
    queryKey: ["students", studentId, kind.noun, "preview", fieldsKey],
    queryFn: () => kind.preview(studentId, draft.fields),
    enabled: draft !== null,
    staleTime: Infinity,
    // Polling here re-rendered the PDF every 30s and swapped the iframe's
    // blob URL underneath it, so the viewer blanked and lost its place
    // mid-read. It also cost a full document render each time.
    refetchInterval: false,
    refetchOnWindowFocus: false,
  });

  /* A blob URL outlives the render that made it, so it has to be revoked by
     hand or every re-preview leaks a PDF for the life of the tab.

     Revoked when a newer one replaces it and when the dialog closes — never
     in the creating effect's own cleanup. StrictMode double-invokes effects
     in development, and that cleanup would revoke the URL the iframe had
     just started loading, leaving an empty viewer. */
  const [previewUrl, setPreviewUrl] = useState(null);
  const liveUrl = useRef(null);
  useEffect(() => {
    if (!preview.data) return;
    const url = URL.createObjectURL(preview.data);
    if (liveUrl.current) URL.revokeObjectURL(liveUrl.current);
    liveUrl.current = url;
    setPreviewUrl(url);
  }, [preview.data]);
  useEffect(
    () => () => {
      if (liveUrl.current) URL.revokeObjectURL(liveUrl.current);
    },
    [],
  );

  const edited = useMemo(() => {
    if (!draft || !source.data) return false;
    return (
      draft.subject !== source.data.subject ||
      draft.body !== source.data.body ||
      fieldsKey !== JSON.stringify(cleaned(source.data.fields))
    );
  }, [draft, source.data, fieldsKey]);

  const setField = (key, value) =>
    setDraft((d) => ({ ...d, fields: cleaned({ ...d.fields, [key]: value }) }));

  const send = useMutation({
    mutationFn: () =>
      kind.issue(studentId, {
        subject: draft.subject,
        body: draft.body,
        fields: draft.fields,
      }),
    onSuccess: async (result) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["reports"] }),
        queryClient.invalidateQueries({ queryKey: kind.candidatesKey }),
      ]);
      onClose();
      // It is filed whether or not the mail server was reachable, so say
      // which of the two actually happened rather than a bare "Done".
      toast[result.email_sent ? "success" : "warning"](
        result.email_sent
          ? `${kind.noun} emailed to ${result.emailed_to}.`
          : `${kind.noun} generated and filed, but the email could not be sent. Check SMTP settings.`,
      );
    },
    onError: (err) =>
      toast.error(
        err instanceof ApiError ? err.detail : `Could not send the ${kind.noun.toLowerCase()}.`,
      ),
  });

  const downloadName = `${kind.filePrefix}_${name.replace(/[^a-z0-9]+/gi, "_")}.pdf`;

  return (
    <Dialog
      open
      onOpenChange={(o) => !o && onClose()}
      title={`${kind.noun} — ${name}`}
      description={`Review it, edit anything that is wrong, then send to ${email}.`}
      className="max-w-3xl"
      footer={
        <>
          {previewUrl && (
            <div className="mr-auto flex items-center gap-4">
              <a
                href={previewUrl}
                download={downloadName}
                className="flex items-center gap-1.5 text-xs font-semibold text-[var(--brand-text)] hover:underline"
              >
                <Download className="size-3.5" aria-hidden /> Download a copy
              </a>
              {/* Not every browser shows a PDF inline — some are set to
                  download them instead, which leaves the frame above blank.
                  This is the way out of that, not a duplicate of Download. */}
              <a
                href={previewUrl}
                target="_blank"
                rel="noreferrer"
                className="flex items-center gap-1.5 text-xs font-semibold text-[var(--brand-text)] hover:underline"
              >
                <ExternalLink className="size-3.5" aria-hidden /> Open in a new tab
              </a>
            </div>
          )}
          <Button
            type="button"
            variant="secondary"
            onClick={() => setEditing((e) => !e)}
            disabled={!draft}
          >
            <Pencil className="size-3.5" aria-hidden /> {editing ? "Done editing" : "Edit"}
          </Button>
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={() => send.mutate()} loading={send.isPending} disabled={!draft}>
            <Send className="size-4" aria-hidden /> Send email
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        {alreadyIssued && (
          <p className="rounded-md border border-warn/30 bg-warn-subtle px-3 py-2 text-xs text-warn-text">
            A {kind.noun.toLowerCase()} has already been sent to {name}. Sending again will deliver
            a second copy.
          </p>
        )}

        {source.isError && (
          <p className="rounded-md border border-danger/30 bg-danger-subtle px-3 py-2 text-xs text-danger-text">
            {source.error instanceof ApiError
              ? source.error.detail
              : `Could not load this ${kind.noun.toLowerCase()}.`}
          </p>
        )}

        {preview.isError && (
          <p className="rounded-md border border-danger/30 bg-danger-subtle px-3 py-2 text-xs text-danger-text">
            {preview.error instanceof ApiError
              ? preview.error.detail
              : "Could not render the preview."}
          </p>
        )}

        {editing && draft && (
          <div className="flex flex-col gap-4 rounded-lg border border-line bg-subtle p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h4 className="text-xs font-bold tracking-wide text-fg uppercase">
                  Edit this {kind.noun.toLowerCase()}
                </h4>
                <p className="mt-0.5 text-[11px] text-fg-muted">
                  Applies to this {kind.noun.toLowerCase()} only. The student record is left alone.
                </p>
              </div>
              {edited && (
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => setDraft(draftFrom(source.data))}
                >
                  <RotateCcw className="size-3.5" aria-hidden /> Reset
                </Button>
              )}
            </div>

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              {kind.fields.map((f) => (
                <Field key={f.key} label={f.label}>
                  {f.mentors ? (
                    <select
                      className={selectClass}
                      value={draft.fields[f.key] ?? ""}
                      onChange={(e) => setField(f.key, e.target.value)}
                    >
                      <option value="">— Leave unsigned —</option>
                      {(mentors.data ?? []).map((m) => (
                        <option key={m.id} value={m.id}>
                          {m.name}
                          {/* The list is already the mentors for this domain,
                              so saying so on each row would be noise. The
                              marker only earns its place when the domain is
                              unknown and everyone is being offered. */}
                          {m.teaches_domain ? "" : "  ·  other domains"}
                        </option>
                      ))}
                    </select>
                  ) : f.choices ? (
                    <select
                      className={selectClass}
                      value={draft.fields[f.key] ?? ""}
                      onChange={(e) => setField(f.key, e.target.value)}
                    >
                      <option value="">— None —</option>
                      {withCurrent(choices.data?.[f.choices], draft.fields[f.key]).map((c) => (
                        <option key={c} value={c}>
                          {c}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <Input
                      value={draft.fields[f.key] ?? ""}
                      onChange={(e) => setField(f.key, e.target.value)}
                    />
                  )}
                </Field>
              ))}
            </div>

            <div className="border-t border-line pt-3">
              <Field label="Email subject">
                <Input
                  value={draft.subject}
                  onChange={(e) => setDraft((d) => ({ ...d, subject: e.target.value }))}
                />
              </Field>
              <Field
                label="Email message"
                hint="The body of the email the PDF is attached to."
                className="mt-3"
              >
                <textarea
                  rows={12}
                  className="w-full rounded-md border border-line bg-surface px-3 py-2 text-xs text-fg"
                  value={draft.body}
                  onChange={(e) => setDraft((d) => ({ ...d, body: e.target.value }))}
                />
              </Field>
            </div>
          </div>
        )}

        {/* The preview endpoint renders the same bytes the send will attach,
            edits included, so what is on screen is what arrives. */}
        {preview.data ? (
          <Suspense
            fallback={
              <div className="flex h-[60vh] w-full items-center justify-center rounded-md border border-line bg-subtle">
                <LoadingState label={`Rendering the ${kind.noun.toLowerCase()}…`} />
              </div>
            }
          >
            <PdfPreview
              file={preview.data}
              label={`${kind.noun} for ${name}`}
              className="max-h-[60vh] overflow-y-auto rounded-md border border-line bg-subtle p-3"
            />
          </Suspense>
        ) : (
          <div className="flex h-[60vh] w-full items-center justify-center rounded-md border border-line bg-subtle">
            <LoadingState label={`Rendering the ${kind.noun.toLowerCase()}…`} />
          </div>
        )}
      </div>
    </Dialog>
  );
}

export function OfferLetterDialog(props) {
  return <IssueDocumentDialog kind={OFFER_LETTER} {...props} />;
}

export function CertificateDialog(props) {
  return <IssueDocumentDialog kind={CERTIFICATE} {...props} />;
}
