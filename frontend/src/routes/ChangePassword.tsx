import { zodResolver } from "@hookform/resolvers/zod";
import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { z } from "zod";

import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { SESSION_KEY, useAuth } from "@/features/auth/AuthProvider";
import { authApi } from "@/features/auth/api";
import { ApiError } from "@/lib/api";

const schema = z
  .object({
    current_password: z.string().min(1, "Enter your current password."),
    new_password: z
      .string()
      .min(10, "Use at least 10 characters.")
      .refine((v) => new TextEncoder().encode(v).length <= 72, "Password is too long."),
    confirm_password: z.string().min(1, "Confirm your new password."),
  })
  .refine((v) => v.new_password === v.confirm_password, {
    path: ["confirm_password"],
    message: "Passwords do not match.",
  })
  .refine((v) => v.new_password !== v.current_password, {
    path: ["new_password"],
    message: "Choose a password different from your current one.",
  });

type FormValues = z.infer<typeof schema>;

export default function ChangePassword() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [formError, setFormError] = useState("");

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  const forced = user?.must_change_password ?? false;

  async function onSubmit(values: FormValues) {
    setFormError("");
    try {
      await authApi.changePassword(values.current_password, values.new_password);
      await queryClient.invalidateQueries({ queryKey: SESSION_KEY });
      toast.success("Password updated.");
      navigate("/", { replace: true });
    } catch (err) {
      setFormError(err instanceof ApiError ? err.detail : "Could not update your password.");
    }
  }

  return (
    <div className="mx-auto w-full max-w-lg px-6 py-12">
      <Card>
        <CardHeader
          title={forced ? "Choose a new password" : "Change your password"}
          description={
            forced
              ? "Your account was set up with a temporary password. Pick your own before continuing."
              : "You will stay signed in on this device; other sessions will be signed out."
          }
        />
        <CardBody>
          <form onSubmit={handleSubmit(onSubmit)} noValidate className="flex flex-col gap-4">
            <Field label="Current password" error={errors.current_password?.message} required>
              <Input type="password" autoComplete="current-password" {...register("current_password")} />
            </Field>

            <Field
              label="New password"
              error={errors.new_password?.message}
              hint="At least 10 characters."
              required
            >
              <Input type="password" autoComplete="new-password" {...register("new_password")} />
            </Field>

            <Field label="Confirm new password" error={errors.confirm_password?.message} required>
              <Input type="password" autoComplete="new-password" {...register("confirm_password")} />
            </Field>

            {formError && (
              <p
                role="alert"
                className="rounded-md border border-danger/30 bg-danger-subtle px-3 py-2 text-xs font-medium text-danger-text"
              >
                {formError}
              </p>
            )}

            <Button type="submit" loading={isSubmitting} className="mt-2 self-start">
              Update password
            </Button>
          </form>
        </CardBody>
      </Card>
    </div>
  );
}
