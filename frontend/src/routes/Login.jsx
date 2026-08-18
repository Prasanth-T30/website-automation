import { zodResolver } from "@hookform/resolvers/zod";
import { Moon, Sun } from "lucide-react";
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
export default function Login() {
  const { login, user, isLoading } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const { theme, toggle } = useTheme();
  const [formError, setFormError] = useState("");
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
      {/* Brand panel — hidden on small screens where it would just push the form down. */}
      <aside className="login-hero-gradient relative hidden flex-col justify-between overflow-hidden p-14 lg:flex">
        <div
          aria-hidden
          className="login-hero-glow pointer-events-none absolute -top-55 -right-35 size-130 rounded-full"
          style={{ background: "radial-gradient(circle, rgb(21 181 184 / 0.35), transparent 62%)" }}
        />
        <div className="relative flex items-center gap-3">
          <img src="/brand/logo-icon.png" alt="Dvein Innovations" className="size-10.5" />
          <div className="leading-tight">
            <p className="text-[15px] font-extrabold tracking-widest text-white">DVEIN</p>
            <p className="mt-0.5 text-[9px] font-semibold tracking-[0.28em] text-white/55">
              INNOVATIONS
            </p>
          </div>
        </div>
        <div className="relative max-w-115">
          <p className="mb-4.5 text-[10px] font-semibold tracking-[0.3em] text-white/50">
            HRM CONSOLE
          </p>
          <h2 className="font-display text-[52px] leading-[1.05] font-normal tracking-tight text-white">
            One pipeline, from first enquiry to{" "}
            <em className="text-accent-300 italic">certificate.</em>
          </h2>
          <p className="mt-5.5 max-w-100 text-sm leading-relaxed text-white/66">
            Applications arrive from the website, your team claims them, and every payment, batch
            and record stays attached to the person who owns it.
          </p>
        </div>
        <p className="relative text-[11px] tracking-wide text-white/45">
          Dvein Innovations · Chennai
        </p>
      </aside>

      <main className="relative flex items-center justify-center px-6 py-12">
        <button
          type="button"
          onClick={toggle}
          aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}
          className="absolute top-7 right-7 flex size-9.5 items-center justify-center rounded-[11px] border border-line bg-surface text-fg-secondary transition-colors hover:bg-subtle"
        >
          {theme === "dark" ? <Sun className="size-4.5" /> : <Moon className="size-4.5" />}
        </button>

        <div className="w-full max-w-sm">
          <img src="/brand/logo-icon.png" alt="" className="mb-6 size-11 lg:hidden" />

          <h1 className="font-display text-[40px] leading-none font-normal tracking-tight text-fg">
            Welcome back
          </h1>
          <p className="mt-2 mb-8.5 text-[13.5px] text-fg-muted">
            Sign in to the Dvein HRM console.
          </p>

          <form onSubmit={handleSubmit(onSubmit)} noValidate className="flex flex-col gap-4">
            <Field label="Email" error={errors.email?.message} required>
              <Input
                type="email"
                autoComplete="username"
                autoFocus
                placeholder="you@dvein.in"
                {...register("email")}
              />
            </Field>

            <Field label="Password" error={errors.password?.message} required>
              <Input type="password" autoComplete="current-password" {...register("password")} />
            </Field>

            {formError && (
              <p
                role="alert"
                className="rounded-md border border-danger/30 bg-danger-subtle px-3 py-2 text-xs font-medium text-danger-text"
              >
                {formError}
              </p>
            )}

            <Button type="submit" size="lg" loading={isSubmitting} className="mt-2">
              Sign in
            </Button>
          </form>

          <p className="mt-6 text-xs text-fg-muted">
            Forgotten your password? Your administrator can issue a new one from the Users screen.
          </p>
        </div>
      </main>
    </div>
  );
}
