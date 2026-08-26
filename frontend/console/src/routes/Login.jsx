import { zodResolver } from "@hookform/resolvers/zod";
import {
  Award,
  Eye,
  EyeOff,
  MessageSquare,
  Moon,
  Search,
  ShieldCheck,
  Sun,
  TrendingUp,
  UserRound,
} from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { z } from "zod";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { useAuth } from "@/features/auth/AuthProvider";
import { ApiError } from "@/lib/api";
import { useTheme } from "@/lib/theme";

const schema = z.object({
  email: z.string().min(1, "Email is required.").email("Enter a valid email address."),
  password: z.string().min(1, "Password is required."),
});

/* The journey the console actually runs, in the order it happens. Five steps
   because that is how many stages a student passes through — an applicant
   becomes a student becomes a certificate holder, and each stage is a screen
   in the app rather than a slogan. */
const JOURNEY = [
  { icon: MessageSquare, label: "Application" },
  { icon: Search, label: "Review" },
  { icon: UserRound, label: "Enrol" },
  { icon: TrendingUp, label: "Track" },
  { icon: Award, label: "Certify" },
];

export default function Login() {
  const { login, user, isLoading } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const { theme, toggle } = useTheme();
  const [formError, setFormError] = useState("");
  /* Typing a password you cannot see is a coin flip, and the one on this
     screen was very likely handed over by an administrator. */
  const [showPassword, setShowPassword] = useState(false);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm({ resolver: zodResolver(schema) });

  if (!isLoading && user) return <Navigate to="/" replace />;

  async function onSubmit(values) {
    setFormError("");
    try {
      const signedIn = await login(values.email, values.password);
      const from = location.state?.from;
      navigate(signedIn.must_change_password ? "/change-password" : (from ?? "/"), {
        replace: true,
      });
    } catch (err) {
      setFormError(
        err instanceof ApiError ? err.detail : "Something went wrong. Please try again.",
      );
    }
  }

  return (
    <div className="grid min-h-dvh lg:grid-cols-[1.05fr_0.95fr]">
      {/* Brand panel — hidden on small screens where it would only push the
          form below the fold. */}
      <aside className="login-hero-gradient relative hidden flex-col items-center justify-center overflow-hidden px-14 py-16 lg:flex">
        {/* The sweep across the lower left, drawn rather than imported so it
            scales with the panel instead of pixelating at wide widths. */}
        <svg
          aria-hidden
          viewBox="0 0 400 260"
          preserveAspectRatio="none"
          className="pointer-events-none absolute -bottom-px left-0 h-70 w-full"
        >
          <path d="M0 260V96c74 46 150 60 228 40 62-16 118-52 172-104v228Z" fill="rgb(255 255 255 / 0.05)" />
          <path d="M0 260V150c66 38 134 48 202 30 56-14 108-44 158-88v168Z" fill="rgb(255 255 255 / 0.045)" />
        </svg>

        <div className="relative flex w-full max-w-125 flex-col items-center text-center">
          <img
            src="/brand/logo.png"
            alt="DVein Innovations"
            className="mb-11 w-full max-w-90"
          />

          <h2 className="font-display text-[62px] leading-none font-normal tracking-[0.06em] text-white">
            HRM CONSOLE
          </h2>
          <p className="mt-5 font-display text-[25px] leading-tight text-accent-300 italic">
            From first enquiry to certificate.
          </p>

          {/* The five stages, joined by a single rule so they read as one
              pipeline rather than five unrelated badges. */}
          <ol className="relative mt-16 flex w-full items-start justify-between">
            <span
              aria-hidden
              className="absolute top-7 right-7 left-7 h-px bg-accent-300/40"
            />
            {JOURNEY.map(({ icon: Icon, label }) => (
              <li key={label} className="relative flex flex-col items-center gap-3">
                <span className="login-hero-gradient flex size-14 items-center justify-center rounded-full border border-accent-300/55 text-accent-300">
                  <Icon className="size-5.5" strokeWidth={1.6} aria-hidden />
                </span>
                <span className="text-[13px] font-medium tracking-wide text-white/80">
                  {label}
                </span>
              </li>
            ))}
          </ol>
        </div>
      </aside>

      <main className="relative flex items-center justify-center px-6 py-12">
        <button
          type="button"
          onClick={toggle}
          aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}
          className="absolute top-8 right-8 flex h-9 w-16 items-center rounded-full border border-line bg-surface px-1.5 transition-colors hover:bg-subtle"
        >
          <span className="pointer-events-none flex size-6 items-center justify-center text-fg-secondary">
            {theme === "dark" ? <Sun className="size-4" /> : <Moon className="size-4" />}
          </span>
          {/* The knob rests on the side it would move to, so the control shows
              which theme is on rather than only what pressing it does. */}
          <span
            className={`pointer-events-none size-6 rounded-full bg-brand transition-transform duration-200 ${
              theme === "dark" ? "translate-x-0" : "translate-x-4"
            }`}
          />
        </button>

        <div className="w-full max-w-sm">
          <img src="/brand/logo.png" alt="DVein Innovations" className="mb-8 w-52 lg:hidden" />

          <h1 className="font-display text-[44px] leading-none font-normal tracking-tight text-fg">
            Welcome back
          </h1>
          <p className="mt-3 mb-9 text-[14.5px] text-fg-muted">
            Sign in to the DVein HRM console.
          </p>

          <form onSubmit={handleSubmit(onSubmit)} noValidate className="flex flex-col gap-5">
            <Field label="Email address" error={errors.email?.message} required>
              <Input
                type="email"
                autoComplete="username"
                autoFocus
                placeholder="you@dvein.in"
                {...register("email")}
              />
            </Field>

            <Field label="Password" error={errors.password?.message} required>
              <div className="relative">
                <Input
                  type={showPassword ? "text" : "password"}
                  autoComplete="current-password"
                  className="pr-11"
                  {...register("password")}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  className="absolute top-1/2 right-3 -translate-y-1/2 text-fg-muted transition-colors hover:text-fg"
                >
                  {showPassword ? <EyeOff className="size-4.5" /> : <Eye className="size-4.5" />}
                </button>
              </div>
            </Field>

            {formError && (
              <p
                role="alert"
                className="rounded-md border border-danger/30 bg-danger-subtle px-3 py-2 text-xs font-medium text-danger-text"
              >
                {formError}
              </p>
            )}

            <Button type="submit" size="lg" loading={isSubmitting} className="mt-1 h-12">
              Sign in
            </Button>
          </form>

          <p className="mt-7 flex items-center gap-2.5 text-[13px] text-fg-muted">
            <ShieldCheck className="size-4.5 shrink-0 text-accent" aria-hidden />
            Need help? Contact your administrator.
          </p>
        </div>
      </main>
    </div>
  );
}
