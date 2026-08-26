import { useQuery } from "@tanstack/react-query";
import { addDays, format, parseISO } from "date-fns";
import { Briefcase, Check, CheckCircle2, Code2, Upload, X } from "lucide-react";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { Button } from "@/components/ui/Button";
import { Card, CardBody } from "@/components/ui/Card";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { publicApi } from "@/features/public/api";
import { ApiError } from "@/lib/api";
import { cn } from "@/lib/cn";
const STEPS = ["Personal", "Category", "Programme", "Payment"];
const CATEGORY_META = {
  Internship: { icon: Briefcase, blurb: "Hands-on, project-based training", domainLabel: "Domain" },
  Course: { icon: Check, blurb: "Structured, instructor-led learning", domainLabel: "Course Name" },
  Project: {
    icon: Code2,
    blurb: "A single deliverable, guided by our team",
    domainLabel: "Project Name",
  },
};
const EXPERIENCE_CHOICES = [
  "Less than 1 year",
  "1 year",
  "2 years",
  "3 years",
  "4 years",
  "5+ years",
];
function durationToDays(duration) {
  const n = parseInt(duration, 10);
  return Number.isFinite(n) ? n : 30;
}
export default function Apply() {
  const [step, setStep] = useState(0);
  const [file, setFile] = useState(null);
  const [fileError, setFileError] = useState("");
  const [submitError, setSubmitError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);
  const choices = useQuery({ queryKey: ["public", "choices"], queryFn: publicApi.choices });
  const {
    register,
    handleSubmit,
    watch,
    setValue,
    trigger,
    formState: { errors },
  } = useForm({
    mode: "onTouched",
    defaultValues: {
      applicant_type: "student",
      title: "",
      name: "",
      email: "",
      phone: "",
      college: "",
      place: "",
      department: "",
      year: "",
      category: "",
      domain: "",
      duration: "",
      start_date: "",
      end_date: "",
      amount: "",
      transaction_id: "",
      declaration: false,
    },
  });
  const applicantType = watch("applicant_type");
  const category = watch("category");
  const startDate = watch("start_date");
  const duration = watch("duration");
  useEffect(() => {
    if (!startDate || !duration) return;
    const end = addDays(parseISO(startDate), durationToDays(duration));
    setValue("end_date", format(end, "yyyy-MM-dd"));
  }, [startDate, duration, setValue]);
  const STEP_FIELDS = [
    ["title", "name", "email", "phone", "college", "place"],
    ["category"],
    ["domain", "duration", "start_date", "end_date"],
    ["amount", "transaction_id", "declaration"],
  ];
  async function next() {
    const valid = await trigger(STEP_FIELDS[step]);
    if (valid) setStep((s) => Math.min(s + 1, STEPS.length - 1));
  }
  function onFileChange(f) {
    setFileError("");
    if (!f) {
      setFile(null);
      return;
    }
    if (!["image/jpeg", "image/jpg", "image/png"].includes(f.type)) {
      setFileError("Only JPG or PNG images are accepted.");
      return;
    }
    if (f.size > 5 * 1024 * 1024) {
      setFileError("File must be under 5 MB.");
      return;
    }
    setFile(f);
  }
  async function onSubmit(values) {
    setSubmitError("");
    if (!file) {
      setFileError("Upload your payment screenshot to continue.");
      return;
    }
    setSubmitting(true);
    try {
      const res = await publicApi.submit({ ...values, amount: values.amount }, file);
      setResult({ registrationId: res.registration_id });
    } catch (err) {
      setSubmitError(
        err instanceof ApiError ? err.detail : "Something went wrong. Please try again.",
      );
    } finally {
      setSubmitting(false);
    }
  }
  if (result) {
    return (
      <div className="shell-wash flex min-h-dvh items-center justify-center px-6 py-12">
        <Card className="w-full max-w-md text-center">
          <CardBody className="flex flex-col items-center gap-4 py-10">
            <CheckCircle2 className="size-14 text-success" />
            <h1 className="text-xl font-extrabold text-fg">Registration received</h1>
            <p className="text-sm text-fg-secondary">
              Your reference number is
              <span className="mt-1 block font-mono text-lg font-bold text-fg">
                {result.registrationId}
              </span>
            </p>
            <p className="text-xs text-fg-muted">
              Our team will review your payment and get back to you by email.
            </p>
            <Button className="mt-2" onClick={() => window.location.reload()}>
              Submit another
            </Button>
          </CardBody>
        </Card>
      </div>
    );
  }
  return (
    <div className="shell-wash min-h-dvh px-4 py-10 sm:px-6">
      <div className="mx-auto max-w-2xl">
        <div className="mb-6 flex items-center gap-3">
          <img src="/brand/logo.png" alt="DVein Innovations" className="h-9" />
        </div>

        <Card>
          <CardBody className="!p-6 sm:!p-8">
            <h1 className="text-xl font-extrabold text-fg">Register for a programme</h1>
            <p className="mt-1 text-sm text-fg-muted">
              Step {step + 1} of {STEPS.length} — {STEPS[step]}
            </p>

            <div className="mt-4 h-2 overflow-hidden rounded-full bg-subtle">
              <div
                className="h-full rounded-full bg-gradient-to-r from-brand-500 via-accent-500 to-signal-500 transition-all"
                style={{ width: `${((step + 1) / STEPS.length) * 100}%` }}
              />
            </div>
            <div className="mt-2 flex justify-between text-[11px] font-semibold text-fg-muted">
              {STEPS.map((s, i) => (
                <span key={s} className={i <= step ? "text-[var(--brand-text)]" : undefined}>
                  {s}
                </span>
              ))}
            </div>

            <form onSubmit={handleSubmit(onSubmit)} noValidate className="mt-8 flex flex-col gap-4">
              {/* ── Step 1: Personal ─────────────────────────────────────── */}
              {step === 0 && (
                <>
                  <div className="mb-2 inline-flex self-start rounded-full bg-subtle p-1">
                    {["student", "professional"].map((t) => (
                      <button
                        key={t}
                        type="button"
                        onClick={() => setValue("applicant_type", t)}
                        className={cn(
                          "rounded-full px-4 py-1.5 text-xs font-semibold capitalize transition-colors",
                          applicantType === t ? "bg-surface text-fg shadow-e1" : "text-fg-muted",
                        )}
                      >
                        {t === "student" ? "Student" : "Working professional"}
                      </button>
                    ))}
                  </div>

                  <div className="grid grid-cols-3 gap-3">
                    <Field label="Title" className="col-span-1">
                      <select
                        className="h-10 w-full rounded-md border border-line bg-surface px-3 text-sm text-fg"
                        {...register("title")}
                      >
                        <option value="">—</option>
                        {choices.data?.titles.map((t) => (
                          <option key={t} value={t}>
                            {t}
                          </option>
                        ))}
                      </select>
                    </Field>
                    <Field
                      label="Full name"
                      error={errors.name?.message}
                      required
                      className="col-span-2"
                    >
                      <Input {...register("name", { required: "Full name is required." })} />
                    </Field>
                  </div>

                  <Field label="Email" error={errors.email?.message} required>
                    <Input
                      type="email"
                      {...register("email", {
                        required: "Email is required.",
                        pattern: {
                          value: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
                          message: "Enter a valid email.",
                        },
                      })}
                    />
                  </Field>

                  <Field label="Phone" error={errors.phone?.message} required>
                    <Input
                      type="tel"
                      inputMode="numeric"
                      maxLength={10}
                      {...register("phone", {
                        required: "Phone is required.",
                        pattern: {
                          value: /^[0-9]{10}$/,
                          message: "Enter a 10-digit mobile number.",
                        },
                        onChange: (e) => {
                          e.target.value = e.target.value.replace(/\D/g, "").slice(0, 10);
                        },
                      })}
                    />
                  </Field>

                  <Field
                    label={applicantType === "professional" ? "Company / Organisation" : "College"}
                    error={errors.college?.message}
                    required
                  >
                    <Input {...register("college", { required: "This field is required." })} />
                  </Field>

                  <Field label="Place" error={errors.place?.message} required>
                    <Input {...register("place", { required: "Place is required." })} />
                  </Field>

                  <div className="grid grid-cols-2 gap-3">
                    <Field label={applicantType === "professional" ? "Designation" : "Department"}>
                      <Input {...register("department")} />
                    </Field>
                    <Field label={applicantType === "professional" ? "Total experience" : "Year"}>
                      <select
                        className="h-10 w-full rounded-md border border-line bg-surface px-3 text-sm text-fg"
                        {...register("year")}
                      >
                        <option value="">—</option>
                        {(applicantType === "professional"
                          ? EXPERIENCE_CHOICES
                          : (choices.data?.years ?? [])
                        ).map((y) => (
                          <option key={y} value={y}>
                            {y}
                          </option>
                        ))}
                      </select>
                    </Field>
                  </div>
                </>
              )}

              {/* ── Step 2: Category ─────────────────────────────────────── */}
              {step === 1 && (
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                  {choices.data?.categories.map((c) => {
                    const meta = CATEGORY_META[c] ?? CATEGORY_META.Internship;
                    const Icon = meta.icon;
                    const selected = category === c;
                    return (
                      <button
                        key={c}
                        type="button"
                        onClick={() => setValue("category", c, { shouldValidate: true })}
                        className={cn(
                          "flex flex-col items-center gap-2 rounded-lg border-2 p-5 text-center transition-colors",
                          selected
                            ? "border-brand bg-brand-subtle"
                            : "border-line-subtle hover:border-line",
                        )}
                      >
                        <span className="flex size-11 items-center justify-center rounded-full bg-gradient-to-br from-brand-500 to-accent-500 text-white">
                          <Icon className="size-5" />
                        </span>
                        <span className="text-sm font-bold text-fg">{c}</span>
                        <span className="text-xs text-fg-muted">{meta.blurb}</span>
                        {selected && <Check className="size-4 text-brand" />}
                      </button>
                    );
                  })}
                  {errors.category && (
                    <p className="col-span-full text-xs text-danger-text">
                      {errors.category.message}
                    </p>
                  )}
                </div>
              )}

              {/* ── Step 3: Programme ────────────────────────────────────── */}
              {step === 2 && (
                <>
                  <Field
                    label={CATEGORY_META[category]?.domainLabel ?? "Domain"}
                    error={errors.domain?.message}
                    required
                  >
                    <select
                      className="h-10 w-full rounded-md border border-line bg-surface px-3 text-sm text-fg"
                      {...register("domain", { required: "Please choose one." })}
                    >
                      <option value="">Select…</option>
                      {choices.data?.domains.map((d) => (
                        <option key={d} value={d}>
                          {d}
                        </option>
                      ))}
                    </select>
                  </Field>

                  <Field label="Duration" error={errors.duration?.message} required>
                    <select
                      className="h-10 w-full rounded-md border border-line bg-surface px-3 text-sm text-fg"
                      {...register("duration", { required: "Please choose a duration." })}
                    >
                      <option value="">Select…</option>
                      {choices.data?.durations.map((d) => (
                        <option key={d} value={d}>
                          {d}
                        </option>
                      ))}
                    </select>
                  </Field>

                  <div className="grid grid-cols-2 gap-3">
                    <Field label="Start date" error={errors.start_date?.message} required>
                      <Input
                        type="date"
                        min={format(new Date(), "yyyy-MM-dd")}
                        {...register("start_date", { required: "Pick a start date." })}
                      />
                    </Field>
                    <Field label="End date" hint="Calculated automatically">
                      <Input type="date" readOnly {...register("end_date")} />
                    </Field>
                  </div>
                </>
              )}

              {/* ── Step 4: Payment ──────────────────────────────────────── */}
              {step === 3 && (
                <>
                  <Field label="Amount paid (₹)" error={errors.amount?.message} required>
                    <Input
                      type="number"
                      step="0.01"
                      {...register("amount", {
                        required: "Amount is required.",
                        min: { value: 0.01, message: "Enter a valid amount." },
                      })}
                    />
                  </Field>

                  <Field
                    label="Transaction ID"
                    error={errors.transaction_id?.message}
                    hint="UPI reference / bank transaction ID"
                    required
                  >
                    <Input
                      {...register("transaction_id", { required: "Transaction ID is required." })}
                    />
                  </Field>

                  <Field label="Payment screenshot" error={fileError} required>
                    {!file ? (
                      <label className="flex cursor-pointer flex-col items-center gap-2 rounded-md border-2 border-dashed border-line px-4 py-8 text-center transition-colors hover:border-brand">
                        <Upload className="size-6 text-fg-muted" />
                        <span className="text-xs text-fg-muted">
                          Click to choose file (max 5 MB, JPG/PNG)
                        </span>
                        <input
                          type="file"
                          accept="image/jpeg,image/jpg,image/png"
                          className="hidden"
                          onChange={(e) => onFileChange(e.target.files?.[0] ?? null)}
                        />
                      </label>
                    ) : (
                      <div className="flex items-center justify-between rounded-md border border-line px-3 py-2">
                        <span className="truncate text-xs text-fg-secondary">{file.name}</span>
                        <button
                          type="button"
                          onClick={() => onFileChange(null)}
                          aria-label="Remove file"
                        >
                          <X className="size-4 text-fg-muted" />
                        </button>
                      </div>
                    )}
                  </Field>

                  <label className="flex items-start gap-2 text-xs text-fg-secondary">
                    <input
                      type="checkbox"
                      className="mt-0.5"
                      {...register("declaration", { required: true })}
                    />
                    I confirm that the information provided is correct.
                  </label>
                  {errors.declaration && (
                    <p className="text-xs text-danger-text">
                      You must confirm the declaration to submit.
                    </p>
                  )}

                  {submitError && (
                    <p
                      role="alert"
                      className="rounded-md border border-danger/30 bg-danger-subtle px-3 py-2 text-xs font-medium text-danger-text"
                    >
                      {submitError}
                    </p>
                  )}
                </>
              )}

              <div className="mt-4 flex justify-between">
                <Button
                  type="button"
                  variant="secondary"
                  disabled={step === 0}
                  onClick={() => setStep((s) => Math.max(s - 1, 0))}
                >
                  Back
                </Button>
                {step < STEPS.length - 1 ? (
                  <Button type="button" onClick={next}>
                    Continue
                  </Button>
                ) : (
                  <Button type="submit" loading={submitting}>
                    Submit registration
                  </Button>
                )}
              </div>
            </form>
          </CardBody>
        </Card>
      </div>
    </div>
  );
}
