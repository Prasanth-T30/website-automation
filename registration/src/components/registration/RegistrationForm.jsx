import { useEffect, useMemo, useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { FiBookOpen, FiBriefcase, FiCheck, FiCode, FiUser, FiX } from "react-icons/fi";
import { toast } from "react-toastify";
import ReactDatePicker from "react-datepicker";
import "react-datepicker/dist/react-datepicker.css";

// Some bundlers (Vite's dev pre-bundler in particular) double-wrap this package's
// default export, turning it into { default: DatePicker, ... } instead of the
// component itself. Unwrap it defensively so it works in both dev and prod builds.
const DatePicker = ReactDatePicker.default ?? ReactDatePicker;

import Button from "../common/Button";
import Input from "../common/Input";
import { CATEGORY_LABELS, DOMAIN_CHOICES, DURATION_CHOICES, MODE_CHOICES, TITLE_CHOICES, YEAR_CHOICES } from "../../utils/constants";
import { submitRegistration } from "../../services/registrationService";
import { useAutofillSync } from "../../hooks/useAutofillSync";
import { verifyPaymentScreenshot } from "../../utils/paymentVerification";
import { isValidEmail, isValidPhone } from "../../utils/validators";
import PaymentUpload from "./PaymentUpload";

// Converts a Date (or date-like value) to a "yyyy-MM-dd" string for form/API use.
const toISODate = (value) => {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const yyyy = date.getFullYear();
  const mm = String(date.getMonth() + 1).padStart(2, "0");
  const dd = String(date.getDate()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}`;
};

// Parses a "yyyy-MM-dd" string back into a Date object for the picker's `selected` prop.
const fromISODate = (value) => {
  if (!value) return null;
  const date = new Date(`${value}T00:00:00`);
  return Number.isNaN(date.getTime()) ? null : date;
};

const CATEGORY_CARDS = [
  { value: "Internship", title: "Internship", note: "Hands-on placement with a mentor", icon: FiBriefcase, accent: "from-primary-500 to-accent-500" },
  { value: "Course", title: "Course", note: "Structured training programme with placement", icon: FiBookOpen, accent: "from-[#6A5AE0] to-accent-500" },
  { value: "Project", title: "Project", note: "Guided build with a deliverable", icon: FiCode, accent: "from-[#E08A3C] to-[#7DC244]" },
];

const STEPS = [
  { title: "Personal details", short: "Personal" },
  { title: "Category", short: "Category" },
  { title: "Programme", short: "Programme" },
  { title: "Payment", short: "Payment" },
];

const RegistrationForm = () => {
  const navigate = useNavigate();
  const [file, setFile] = useState(null);
  const [step, setStep] = useState(1);
  const [submitting, setSubmitting] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [resultOverlay, setResultOverlay] = useState(null); // { status: "success" | "failure", message }
  const formRef = useRef(null);
  const startDatePickerRef = useRef(null);
  const endDatePickerRef = useRef(null);
  const {
    register,
    handleSubmit,
    setValue,
    getValues,
    trigger,
    watch,
    formState: { errors },
  } = useForm({
    mode: "onTouched",
    reValidateMode: "onChange",
    defaultValues: { applicant_type: "student", category: "Internship" },
  });

  useAutofillSync(formRef, setValue);

  const applicantType = watch("applicant_type") || "student";
  const selectedCategory = watch("category") || "Internship";
  const categoryLabels = CATEGORY_LABELS[selectedCategory] || CATEGORY_LABELS.Internship;
  const isProfessional = applicantType === "professional";
  const isProjectCategory = selectedCategory === "Project";
  const progress = `${(step / STEPS.length) * 100}%`;

  // Working professionals only register for a Course or a Project — Internship is student-only.
  const categoryCardOptions = isProfessional ? CATEGORY_CARDS.filter((card) => card.value !== "Internship") : CATEGORY_CARDS;

  useEffect(() => {
    if (isProfessional && selectedCategory === "Internship") {
      setValue("category", "Course", { shouldValidate: true, shouldDirty: true });
    }
  }, [isProfessional, selectedCategory, setValue]);

  const startDateValue = watch("start_date");
  const durationValue = watch("duration");
  const endDateValue = watch("end_date");

  // Auto-calculate the end date whenever both a start date and a duration are chosen.
  useEffect(() => {
    if (!startDateValue || !durationValue) return;
    const days = parseInt(durationValue, 10);
    if (Number.isNaN(days)) return;
    const start = fromISODate(startDateValue);
    if (!start) return;
    const end = new Date(start);
    end.setDate(end.getDate() + days);
    setValue("end_date", toISODate(end), { shouldValidate: true, shouldDirty: true });
  }, [startDateValue, durationValue, setValue]);

  // Project registrations don't ask for duration/dates/mode, but the backend still expects
  // those fields to be present — quietly fill in sensible defaults behind the scenes.
  useEffect(() => {
    if (!isProjectCategory) return;
    const values = getValues();
    if (!values.duration) setValue("duration", DURATION_CHOICES[0]);
    if (!values.start_date) setValue("start_date", toISODate(new Date()));
    if (!values.mode) setValue("mode", "Online");
  }, [isProjectCategory, getValues, setValue]);

  const stepFields = useMemo(() => ({
    1: ["salutation", "name", "email", "phone", "college", "place"],
    2: ["category"],
    3: isProjectCategory ? ["project_topic", "domain"] : ["domain", "duration", "start_date", "end_date", "mode"],
    4: ["amount", "transaction_id", "declaration"],
  }), [isProjectCategory]);

  const phoneField = register("phone", {
    required: "Mobile number is required",
    validate: (value) => isValidPhone(value) || "Enter a valid email or mobile number",
  });

  /**
   * Bring the first thing that failed into view.
   *
   * `trigger` reports failure but, unlike `handleSubmit`, never moves focus.
   * On a step whose invalid field sits below the fold that made Continue look
   * like a dead button. Scrolling to the message rather than calling
   * `setFocus` handles the date fields too: those validate a hidden input that
   * cannot take focus, so only their message is reachable.
   */
  const revealFirstError = () => {
    // Let React paint the messages `trigger` just produced. A timeout rather
    // than requestAnimationFrame: rAF is paused in a backgrounded tab, so a
    // form restored into a hidden tab would never reveal its error.
    setTimeout(() => {
      const message = formRef.current?.querySelector("[data-error-message]");
      if (!message) return;
      message.scrollIntoView({ behavior: "smooth", block: "center" });
      const field = message.parentElement?.querySelector(
        "input:not([type=hidden]), select, textarea",
      );
      field?.focus({ preventScroll: true });
    }, 0);
  };

  const goNext = async () => {
    const ok = await trigger(stepFields[step] || []);
    if (!ok) {
      revealFirstError();
      return;
    }
    if (step === 4 && !file) {
      toast.error("Please upload your payment screenshot");
      return;
    }
    setStep((current) => Math.min(4, current + 1));
  };

  const onSubmit = async (values) => {
    if (!file) {
      toast.error("Please upload your payment screenshot");
      return;
    }
    if (!values.declaration) {
      toast.error("Please confirm the declaration to proceed");
      return;
    }

    // Check the payment screenshot against the typed amount and UPI transaction ID.
    // The registration only proceeds once at least two of the three checks pass
    // (looks like a real payment screenshot, amount matches, transaction ID matches).
    setVerifying(true);
    let verification;
    try {
      verification = await verifyPaymentScreenshot(file, values.amount, values.transaction_id);
    } finally {
      setVerifying(false);
    }

    if (!verification.isValid) {
      setResultOverlay({
        status: "failure",
        message: "We couldn't verify this payment screenshot against the amount and UPI transaction ID you entered. Please double-check them and try again.",
      });
      return;
    }

    const formData = new FormData();
    Object.entries(values).forEach(([key, value]) => {
      formData.append(key, key === "declaration" ? (value ? "true" : "false") : value ?? "");
    });
    formData.append("payment_screenshot", file);

    setSubmitting(true);
    try {
      const registration = await submitRegistration(formData);
      setResultOverlay({ status: "success", message: "Your registration has been submitted successfully." });
      setTimeout(() => navigate("/success", { state: { registration } }), 1800);
    } catch (err) {
      // Log the full error so it shows up in the browser console for debugging —
      // the toast only has room for a short, human-readable summary.
      console.error("Registration submission failed:", err);

      let message = "Registration failed. Please try again.";
      if (err?.response) {
        // The server responded, but with an error — surface whatever detail it sent.
        const detail = err.response.data?.detail;
        message =
          (typeof detail === "string" && detail) ||
          err.response.data?.message ||
          `Registration failed (server responded with status ${err.response.status}).`;
      } else if (err?.request) {
        // The request was sent but no response ever came back — almost always means
        // the backend isn't running, is unreachable, or blocked the request (e.g. CORS).
        message = "Could not reach the server. Please make sure the backend is running, then try again.";
      }
      toast.error(message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form ref={formRef} onSubmit={handleSubmit(onSubmit)} className="space-y-6">
      {resultOverlay && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/50 px-4">
          <div className="w-full max-w-sm rounded-2xl bg-white p-8 text-center shadow-2xl">
            <span
              className={`mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full ${
                resultOverlay.status === "success" ? "bg-emerald-100 text-emerald-600" : "bg-red-100 text-red-600"
              }`}
            >
              {resultOverlay.status === "success" ? <FiCheck size={28} /> : <FiX size={28} />}
            </span>
            <h3 className="text-lg font-extrabold text-[#0F1B2D]">
              {resultOverlay.status === "success" ? "Registration Successful" : "Registration Failed"}
            </h3>
            {resultOverlay.message && <p className="mt-2 text-sm font-medium text-[#6B7A90]">{resultOverlay.message}</p>}
            {resultOverlay.status === "failure" && (
              <Button type="button" className="mt-5 w-full" onClick={() => setResultOverlay(null)}>
                Try Again
              </Button>
            )}
          </div>
        </div>
      )}

      <div>
        <div className="mb-3 flex items-center justify-between">
          <span className="text-[11px] font-extrabold uppercase tracking-[.12em] text-[#8494A9]">Step {step} of 4</span>
          <span className="text-[11px] font-bold text-primary-500">{STEPS[step - 1].title}</span>
        </div>
        <div className="h-1 overflow-hidden rounded-full bg-[#E7EDF5]">
          <div className="h-full rounded-full bg-gradient-to-r from-primary-500 via-accent-500 to-[#7DC244] transition-all duration-300" style={{ width: progress }} />
        </div>
        <div className="mt-3 grid grid-cols-4 gap-2 text-[10.5px] font-bold">
          {STEPS.map((item, index) => (
            <span key={item.short} className={index + 1 <= step ? "text-[#2A5488]" : "text-[#A5B2C2]"}>{item.short}</span>
          ))}
        </div>
      </div>

      <input type="hidden" {...register("applicant_type")} />
      <input type="hidden" {...register("category", { required: "Please select a category" })} />

      {step === 1 && (
        <section className="dv-section">
          <div className="mb-4 flex items-center gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-[11px] bg-[#EAF2FB] text-primary-600">
              <FiUser />
            </span>
            <div>
              <h2 className="text-base font-extrabold text-[#0F1B2D]">Personal information</h2>
              <p className="text-xs font-medium text-[#6B7A90]">Tell us who you are. Fields marked * are required.</p>
            </div>
          </div>

          <div className="mb-5">
            <span className="dv-label">I am a</span>
            <div className="grid grid-cols-2 gap-1 rounded-[12px] bg-[#EDF1F7] p-1">
              {[
                ["student", "Student"],
                ["professional", "Working professional"],
              ].map(([value, label]) => (
                <button
                  key={value}
                  type="button"
                  onClick={() => setValue("applicant_type", value, { shouldDirty: true })}
                  className={`h-10 rounded-[9px] text-xs font-extrabold transition ${applicantType === value ? "bg-white text-[#1F3F66] shadow-sm" : "text-[#6B7A90]"}`}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Input as="select" label="Salutation" required error={errors.salutation?.message} {...register("salutation", { required: "Please select a salutation" })}>
              <option value="">Select salutation</option>
              {TITLE_CHOICES.map((t) => <option key={t} value={t}>{t}</option>)}
            </Input>
            <Input label="Full Name" required placeholder="Enter full name" error={errors.name?.message} {...register("name", { required: "Full name is required" })} />
            <Input
              label="Email"
              type="email"
              required
              placeholder="you@example.com"
              error={errors.email?.message}
              {...register("email", {
                required: "Email is required",
                validate: (value) => isValidEmail(value) || "Enter a valid email or mobile number",
              })}
            />
            <Input
              label="Mobile Number"
              required
              type="tel"
              inputMode="numeric"
              maxLength={10}
              placeholder="10-digit mobile number"
              error={errors.phone?.message}
              {...phoneField}
              onChange={(e) => {
                e.target.value = e.target.value.replace(/\D/g, "").slice(0, 10);
                phoneField.onChange(e);
              }}
            />
            <Input label={isProfessional ? "Company / Organisation" : "College Name"} required placeholder={isProfessional ? "Enter company name" : "Enter college name"} error={errors.college?.message} {...register("college", { required: isProfessional ? "Company name is required" : "College name is required" })} />
            <Input label="Place" required placeholder="City / Town" error={errors.place?.message} {...register("place", { required: "Place is required" })} />
            <Input label={isProfessional ? "Designation" : "Department"} placeholder={isProfessional ? "e.g. Software Engineer" : "e.g. CSE, ECE, IT"} {...register("department")} />
            {isProfessional ? (
              <Input as="select" label="Total Experience" {...register("year")}>
                <option value="">Select experience</option>
                <option>Less than 1 year</option>
                <option>1 year</option>
                <option>2 years</option>
                <option>3 years</option>
                <option>4 years</option>
                <option>5+ years</option>
              </Input>
            ) : (
              <Input as="select" label="Year of Study" {...register("year")}>
                <option value="">Select year</option>
                {YEAR_CHOICES.map((y) => <option key={y} value={y}>{y}</option>)}
              </Input>
            )}
          </div>
        </section>
      )}

      {step === 2 && (
        <section className="dv-section">
          <h2 className="mb-1 text-base font-extrabold text-[#0F1B2D]">Choose your category</h2>
          <p className="mb-4 text-xs font-medium text-[#6B7A90]">This decides the programme details we ask for next.</p>
          <div className="grid grid-cols-1 gap-3">
            {categoryCardOptions.map(({ value, title, note, icon: Icon, accent }) => {
              const active = selectedCategory === value;
              return (
                <button
                  key={value}
                  type="button"
                  onClick={() => setValue("category", value, { shouldValidate: true, shouldDirty: true })}
                  className={`flex w-full items-center gap-3 rounded-[14px] border p-3 text-left transition active:scale-[.99] ${
                    active ? "border-primary-500 bg-[#F3F8FD]" : "border-[#E2E9F2] bg-white hover:bg-[#FBFCFE]"
                  }`}
                >
                  <span className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-[11px] bg-gradient-to-br ${accent} text-white`}>
                    <Icon />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block text-sm font-extrabold text-[#0F1B2D]">{title}</span>
                    <span className="block text-xs font-medium text-[#6B7A90]">{note}</span>
                  </span>
                  <span className={`flex h-5 w-5 items-center justify-center rounded-full border ${active ? "border-primary-500 bg-primary-500 text-white" : "border-[#DCE4EE] bg-white"}`}>
                    {active && <FiCheck size={12} />}
                  </span>
                </button>
              );
            })}
          </div>
          {errors.category?.message && <p className="mt-1 text-xs font-medium text-[#C2453F]">{errors.category.message}</p>}
        </section>
      )}

      {step === 3 && (
        <section className="dv-section">
          <h2 className="mb-1 text-base font-extrabold text-[#0F1B2D]">{categoryLabels.section}</h2>
          <p className="mb-4 text-xs font-medium text-[#6B7A90]">
            {isProjectCategory ? "Tell us about the project you'd like to build." : "Choose the domain, duration, and dates for this registration."}
          </p>

          {isProjectCategory ? (
            <div className="mx-auto grid max-w-md grid-cols-1 gap-4">
              <Input
                label="Project Topic"
                required
                placeholder="Enter your project topic"
                error={errors.project_topic?.message}
                {...register("project_topic", { required: "Project topic is required" })}
              />
              <Input as="select" label="Domain Name" required error={errors.domain?.message} {...register("domain", { required: "Please select a domain" })}>
                <option value="">Select domain name</option>
                {DOMAIN_CHOICES.map((d) => <option key={d} value={d}>{d}</option>)}
              </Input>
              {/* Kept for backend compatibility (auto-filled with defaults) — not shown for Project registrations. */}
              <input type="hidden" {...register("duration")} />
              <input type="hidden" {...register("start_date")} />
              <input type="hidden" {...register("end_date")} />
              <input type="hidden" {...register("mode")} />
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <Input as="select" label={categoryLabels.domainField} required error={errors.domain?.message} {...register("domain", { required: `Please select a ${categoryLabels.domainField.toLowerCase()}` })}>
                <option value="">Select {categoryLabels.domainField.toLowerCase()}</option>
                {DOMAIN_CHOICES.map((d) => <option key={d} value={d}>{d}</option>)}
              </Input>
              <Input as="select" label="Duration" required error={errors.duration?.message} {...register("duration", { required: "Please select a duration" })}>
                <option value="">Select duration</option>
                {DURATION_CHOICES.map((d) => <option key={d} value={d}>{d}</option>)}
              </Input>

              <div>
                <span className="dv-label">
                  Start Date <span className="text-[#DC5B5B]">*</span>
                </span>
                <DatePicker
                  ref={startDatePickerRef}
                  selected={fromISODate(startDateValue)}
                  onChange={(date) => setValue("start_date", toISODate(date), { shouldValidate: true, shouldDirty: true })}
                  dateFormat="dd-MM-yyyy"
                  placeholderText="dd-mm-yyyy"
                  className="input-base w-full"
                  wrapperClassName="w-full"
                  minDate={new Date()}
                >
                  <div className="flex justify-end border-t border-[#E7EDF5] px-1 pb-1 pt-2">
                    <button
                      type="button"
                      className="rounded-md bg-primary-500 px-3 py-1 text-xs font-bold text-white"
                      onClick={() => startDatePickerRef.current?.setOpen(false)}
                    >
                      OK
                    </button>
                  </div>
                </DatePicker>
                <input type="hidden" {...register("start_date", { required: "Start date is required" })} />
                {errors.start_date?.message && <p data-error-message className="mt-1 text-xs font-medium text-[#C2453F]">{errors.start_date.message}</p>}
              </div>

              <div>
                <span className="dv-label">
                  End Date <span className="text-[#DC5B5B]">*</span>
                </span>
                <DatePicker
                  ref={endDatePickerRef}
                  selected={fromISODate(endDateValue)}
                  onChange={(date) => setValue("end_date", toISODate(date), { shouldValidate: true, shouldDirty: true })}
                  dateFormat="dd-MM-yyyy"
                  placeholderText="dd-mm-yyyy"
                  className="input-base w-full"
                  wrapperClassName="w-full"
                  minDate={fromISODate(startDateValue) || new Date()}
                >
                  <div className="flex justify-end border-t border-[#E7EDF5] px-1 pb-1 pt-2">
                    <button
                      type="button"
                      className="rounded-md bg-primary-500 px-3 py-1 text-xs font-bold text-white"
                      onClick={() => endDatePickerRef.current?.setOpen(false)}
                    >
                      OK
                    </button>
                  </div>
                </DatePicker>
                <input type="hidden" {...register("end_date", { required: "End date is required" })} />
                {errors.end_date?.message && <p data-error-message className="mt-1 text-xs font-medium text-[#C2453F]">{errors.end_date.message}</p>}
              </div>

              <div className="flex justify-center sm:col-span-2">
                <div className="w-full sm:w-1/2">
                  <Input as="select" label="Mode" required error={errors.mode?.message} {...register("mode", { required: "Please select a mode" })}>
                    <option value="">Select mode</option>
                    {MODE_CHOICES.map((m) => <option key={m} value={m}>{m}</option>)}
                  </Input>
                </div>
              </div>
            </div>
          )}
        </section>
      )}

      {step === 4 && (
        <section className="dv-section">
          <h2 className="mb-1 text-base font-extrabold text-[#0F1B2D]">Payment section</h2>
          <p className="mb-4 text-xs font-medium text-[#6B7A90]">Upload a clear screenshot after completing payment.</p>
          <div className="rounded-2xl border border-[#DEE7F1] bg-[#FBFCFE] p-4">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <Input label="Amount Paid (Rs.)" type="number" step="0.01" required error={errors.amount?.message} {...register("amount", { required: "Amount paid is required" })} />
              <Input label="UPI Transaction ID" required error={errors.transaction_id?.message} {...register("transaction_id", { required: "Transaction ID is required" })} />
            </div>
            <div className="mt-4">
              <PaymentUpload file={file} onChange={setFile} />
            </div>
          </div>

          {/* Free text. Whatever is typed here is shown to the HR reviewing the
              registration, so an applicant can raise anything the form itself
              does not ask about. */}
          <div className="mt-4">
            <label className="mb-1.5 block text-xs font-bold text-[#0F1B2D]" htmlFor="other">
              Other
            </label>
            <textarea
              id="other"
              rows={3}
              maxLength={1000}
              placeholder="Anything else you would like us to know (optional)"
              className="w-full rounded-[14px] border border-[#DCE4EE] bg-white px-4 py-3 text-sm font-medium text-[#0F1B2D] outline-none transition placeholder:text-[#9AA8BC] focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20"
              {...register("other", { maxLength: 1000 })}
            />
            <p className="mt-1 text-[11px] font-medium text-[#8494A9]">
              Optional. Our team sees this when reviewing your registration.
            </p>
          </div>

          <label className="mt-4 flex items-start gap-3 rounded-[14px] border border-[#DCE4EE] bg-white p-4 text-sm font-medium leading-6 text-[#5A6B82]">
            <input type="checkbox" className="mt-1 h-4 w-4 rounded border-[#DCE4EE] text-primary-500 focus:ring-primary-500" {...register("declaration", { required: true })} />
            I confirm that the information provided is correct.
          </label>
        </section>
      )}

      <div className="flex items-center justify-between gap-3 border-t border-[#EEF2F7] pt-5">
        <Button type="button" variant="secondary" className={step === 1 ? "invisible" : ""} onClick={() => setStep((current) => Math.max(1, current - 1))}>
          Back
        </Button>
        {step < 4 ? (
          <Button type="button" onClick={goNext}>
            Continue
          </Button>
        ) : (
          <Button type="submit" loading={submitting || verifying}>
            {verifying ? "Verifying payment..." : "Submit registration"}
          </Button>
        )}
      </div>
    </form>
  );
};

export default RegistrationForm;
