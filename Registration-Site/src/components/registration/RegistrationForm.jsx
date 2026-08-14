import { useMemo, useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { FiBookOpen, FiBriefcase, FiCheck, FiCode, FiUser } from "react-icons/fi";
import { toast } from "react-toastify";

import Button from "../common/Button";
import Input from "../common/Input";
import { CATEGORY_LABELS, DOMAIN_CHOICES, DURATION_CHOICES, TITLE_CHOICES, YEAR_CHOICES } from "../../utils/constants";
import { submitRegistration } from "../../services/registrationService";
import { useAutofillSync } from "../../hooks/useAutofillSync";
import PaymentUpload from "./PaymentUpload";

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
  const formRef = useRef(null);
  const {
    register,
    handleSubmit,
    setValue,
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
  const progress = `${(step / STEPS.length) * 100}%`;

  const stepFields = useMemo(() => ({
    1: ["title", "name", "email", "phone", "college", "place"],
    2: ["category"],
    3: ["domain", "duration", "start_date", "end_date"],
    4: ["amount", "transaction_id", "declaration"],
  }), []);

  const goNext = async () => {
    const ok = await trigger(stepFields[step] || []);
    if (!ok) return;
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

    const formData = new FormData();
    Object.entries(values).forEach(([key, value]) => {
      formData.append(key, key === "declaration" ? (value ? "true" : "false") : value ?? "");
    });
    formData.append("payment_screenshot", file);

    setSubmitting(true);
    try {
      const registration = await submitRegistration(formData);
      navigate("/success", { state: { registration } });
    } catch (err) {
      const message = err?.response?.data?.detail || err?.response?.data?.message || "Registration failed. Please try again.";
      toast.error(message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form ref={formRef} onSubmit={handleSubmit(onSubmit)} className="space-y-6">
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
            <Input as="select" label="Title" required error={errors.title?.message} {...register("title", { required: "Please select a title" })}>
              <option value="">Select title</option>
              {TITLE_CHOICES.map((t) => <option key={t} value={t}>{t}</option>)}
            </Input>
            <Input label="Full Name" required placeholder="Enter full name" error={errors.name?.message} {...register("name", { required: "Full name is required" })} />
            <Input label="Email" type="email" required placeholder="you@example.com" error={errors.email?.message} {...register("email", { required: "Email is required" })} />
            <Input label="Mobile Number" required placeholder="10-digit mobile number" error={errors.phone?.message} {...register("phone", { required: "Mobile number is required" })} />
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
            {CATEGORY_CARDS.map(({ value, title, note, icon: Icon, accent }) => {
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
          <p className="mb-4 text-xs font-medium text-[#6B7A90]">Choose the domain, duration, and dates for this registration.</p>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Input as="select" label={categoryLabels.domainField} required error={errors.domain?.message} {...register("domain", { required: `Please select a ${categoryLabels.domainField.toLowerCase()}` })}>
              <option value="">Select {categoryLabels.domainField.toLowerCase()}</option>
              {DOMAIN_CHOICES.map((d) => <option key={d} value={d}>{d}</option>)}
            </Input>
            <Input as="select" label="Duration" required error={errors.duration?.message} {...register("duration", { required: "Please select a duration" })}>
              <option value="">Select duration</option>
              {DURATION_CHOICES.map((d) => <option key={d} value={d}>{d}</option>)}
            </Input>
            <Input label="Start Date" type="date" required error={errors.start_date?.message} {...register("start_date", { required: "Start date is required" })} />
            <Input label="End Date" type="date" required error={errors.end_date?.message} {...register("end_date", { required: "End date is required" })} />
          </div>
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
          <Button type="submit" loading={submitting}>
            Submit registration
          </Button>
        )}
      </div>
    </form>
  );
};

export default RegistrationForm;
