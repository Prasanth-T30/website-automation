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

type FormValues = z.infer<typeof schema>;

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
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  if (!isLoading && user) return <Navigate to="/" replace />;

  async function onSubmit(values: FormValues) {
    setFormError("");
    try {
      const signedIn = await login(values.email, values.password);
      const from = (location.state as { from?: string } | null)?.from;
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
    <div className="grid min-h-dvh lg:grid-cols-2">
      {/* Brand panel — hidden on small screens where it would just push the form down. */}
      <aside className="brand-gradient relative hidden flex-col justify-between p-12 lg:flex">
        <img src="/brand/logo-icon.png" alt="Dvein Innovations" className="size-12" />
        <div className="max-w-md">
          <h2 className="text-3xl leading-tight font-extrabold text-white">
            One pipeline, from first enquiry to certificate.
          </h2>
          <p className="mt-4 text-sm text-white/85">
            Applications arrive from the website, your team claims them, and every payment,
            batch and record stays attached to the person who owns it.
          </p>
        </div>
        <p className="text-xs text-white/70">Dvein Innovations · Chennai</p>
      </aside>

      <main className="relative flex items-center justify-center px-6 py-12">
        <button
          type="button"
          onClick={toggle}
          aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}
          className="absolute top-6 right-6 flex size-10 items-center justify-center rounded-md border border-line bg-surface text-fg-secondary transition-colors hover:bg-subtle"
        >
          {theme === "dark" ? <Sun className="size-5" /> : <Moon className="size-5" />}
        </button>

        <div className="w-full max-w-sm">
          <img src="/brand/logo-icon.png" alt="" className="mb-6 size-11 lg:hidden" />

          <h1 className="text-2xl font-extrabold tracking-tight text-fg">Welcome back</h1>
          <p className="mt-1 mb-8 text-sm text-fg-muted">
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
            Forgotten your password? Your administrator can issue a new one from the Users
            screen.
          </p>
        </div>
      </main>
    </div>
  );
}
