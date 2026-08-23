import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Copy, KeyRound, Plus, Trash2, UserCog } from "lucide-react";
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
import { Input } from "@/components/ui/Input";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/States";
import { useAuth } from "@/features/auth/AuthProvider";
import { usersApi } from "@/features/users/api";
import { ApiError } from "@/lib/api";
const USERS_KEY = ["admin", "users"];
const createSchema = z.object({
  full_name: z.string().min(2, "Enter a full name."),
  email: z.string().email("Enter a valid email address."),
  password: z
    .string()
    .min(10, "Use at least 10 characters.")
    .refine((v) => new TextEncoder().encode(v).length <= 72, "Password is too long."),
  role: z.enum(["hr", "admin"]),
  phone: z.string().optional(),
});
export default function Users() {
  const queryClient = useQueryClient();
  const { user: currentUser } = useAuth();
  const [createOpen, setCreateOpen] = useState(false);
  const [issued, setIssued] = useState(null);
  const [pendingDelete, setPendingDelete] = useState(null);
  const users = useQuery({ queryKey: USERS_KEY, queryFn: usersApi.list });
  const invalidate = () => queryClient.invalidateQueries({ queryKey: USERS_KEY });
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm({
    resolver: zodResolver(createSchema),
    defaultValues: { role: "hr" },
  });
  const createUser = useMutation({
    mutationFn: (values) => usersApi.create({ ...values, phone: values.phone || null }),
    onSuccess: async (created) => {
      await invalidate();
      setCreateOpen(false);
      reset({ role: "hr" });
      toast.success(`Account created for ${created.full_name}.`);
    },
    onError: (err) =>
      toast.error(err instanceof ApiError ? err.detail : "Could not create the account."),
  });
  const toggleActive = useMutation({
    mutationFn: (u) => usersApi.update(u.id, { is_active: !u.is_active }),
    onSuccess: async (updated) => {
      await invalidate();
      toast.success(`${updated.full_name} ${updated.is_active ? "reactivated" : "deactivated"}.`);
    },
    onError: (err) => toast.error(err instanceof ApiError ? err.detail : "Update failed."),
  });
  const resetPassword = useMutation({
    mutationFn: (u) => usersApi.resetPassword(u.id).then((r) => ({ r, name: u.full_name })),
    onSuccess: async ({ r, name }) => {
      await invalidate();
      setIssued({ name, password: r.temporary_password });
    },
    onError: (err) => toast.error(err instanceof ApiError ? err.detail : "Reset failed."),
  });
  const deleteUser = useMutation({
    mutationFn: (u) => usersApi.delete(u.id).then(() => u.full_name),
    onSuccess: async (name) => {
      await invalidate();
      setPendingDelete(null);
      toast.success(`${name}'s account has been deleted.`);
    },
    onError: (err) =>
      toast.error(err instanceof ApiError ? err.detail : "Could not delete the account."),
  });
  return (
    <>
      <PageHeader
        title="Users"
        description="The administrator and the HR team. Deactivate to suspend access reversibly; delete only for accounts created in error — it cannot be undone."
        action={
          <Button onClick={() => setCreateOpen(true)}>
            <Plus className="size-4" /> Add user
          </Button>
        }
      />

      <div className="p-6">
        <Card className="overflow-hidden">
          {users.isPending && <LoadingState label="Loading users…" />}

          {users.isError && (
            <ErrorState
              description={
                users.error instanceof ApiError ? users.error.detail : "Could not load users."
              }
              onRetry={() => users.refetch()}
            />
          )}

          {users.data?.length === 0 && (
            <EmptyState
              icon={<UserCog className="size-6" />}
              title="No accounts yet"
              description="Run `python -m app.cli seed` to create the administrator and three HR accounts."
            />
          )}

          {users.data && users.data.length > 0 && (
            <div className="scroll-x">
              <table className="w-full min-w-[720px] text-sm">
                <thead>
                  <tr className="border-b border-line-subtle bg-subtle/60 text-left">
                    {["Name", "Email", "Role", "Status", "Last sign-in", ""].map((h) => (
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
                  {users.data.map((u) => {
                    const isSelf = u.id === currentUser?.id;
                    return (
                      <tr key={u.id} className="border-b border-line-subtle last:border-0">
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-2.5">
                            <Avatar name={u.full_name} size="sm" />
                            <span className="font-medium text-fg">{u.full_name}</span>
                            {isSelf && <span className="text-xs text-fg-muted">(you)</span>}
                          </div>
                        </td>
                        <td className="px-4 py-3 text-fg-secondary">{u.email}</td>
                        <td className="px-4 py-3">
                          <Badge tone={u.role === "admin" ? "brand" : "neutral"}>
                            {u.role === "admin" ? "Administrator" : "HR"}
                          </Badge>
                        </td>
                        <td className="px-4 py-3">
                          <Badge tone={u.is_active ? "success" : "danger"}>
                            {u.is_active ? "Active" : "Deactivated"}
                          </Badge>
                        </td>
                        <td className="px-4 py-3 text-xs text-fg-muted">
                          {u.last_login_at ? new Date(u.last_login_at).toLocaleString() : "Never"}
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex justify-end gap-1">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => resetPassword.mutate(u)}
                              loading={resetPassword.isPending}
                            >
                              <KeyRound className="size-3.5" /> Reset
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              disabled={isSelf}
                              title={isSelf ? "You cannot deactivate your own account" : undefined}
                              onClick={() => toggleActive.mutate(u)}
                            >
                              {u.is_active ? "Deactivate" : "Reactivate"}
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              disabled={isSelf}
                              title={
                                isSelf ? "You cannot delete your own account" : "Delete permanently"
                              }
                              className="text-danger hover:bg-danger-subtle hover:text-danger-text"
                              onClick={() => setPendingDelete(u)}
                            >
                              <Trash2 className="size-3.5" />
                            </Button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>

      {/* ── Create ─────────────────────────────────────────────────────── */}
      <Dialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        title="Add a user"
        description="The account starts with a temporary password that must be changed at first sign-in."
      >
        <form
          id="create-user"
          onSubmit={handleSubmit((v) => createUser.mutateAsync(v))}
          noValidate
          className="flex flex-col gap-4"
        >
          <Field label="Full name" error={errors.full_name?.message} required>
            <Input autoFocus {...register("full_name")} />
          </Field>
          <Field label="Email" error={errors.email?.message} required>
            <Input type="email" placeholder="name@dvein.in" {...register("email")} />
          </Field>
          <Field label="Phone" error={errors.phone?.message}>
            <Input type="tel" {...register("phone")} />
          </Field>
          <Field label="Role" error={errors.role?.message} required>
            <select
              className="h-10 w-full rounded-md border border-line bg-surface px-3 text-sm text-fg"
              {...register("role")}
            >
              <option value="hr">HR</option>
              <option value="admin">Administrator</option>
            </select>
          </Field>
          <Field
            label="Temporary password"
            error={errors.password?.message}
            hint="At least 10 characters. Share it with them directly."
            required
          >
            <Input type="text" autoComplete="off" {...register("password")} />
          </Field>

          <div className="mt-2 flex justify-end gap-2">
            <Button type="button" variant="secondary" onClick={() => setCreateOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" loading={isSubmitting}>
              Create account
            </Button>
          </div>
        </form>
      </Dialog>

      {/* ── Password issued (shown exactly once) ───────────────────────── */}
      <Dialog
        open={issued !== null}
        onOpenChange={(o) => !o && setIssued(null)}
        title="Temporary password issued"
        description="This is shown once and cannot be recovered. Copy it before closing."
        footer={<Button onClick={() => setIssued(null)}>Done</Button>}
      >
        <p className="text-sm text-fg-secondary">
          {issued?.name} has been signed out of all sessions and must set a new password at next
          sign-in.
        </p>
        <div className="mt-3 flex items-center gap-2 rounded-md border border-line bg-subtle px-3 py-2">
          <code className="flex-1 font-mono text-sm break-all text-fg">{issued?.password}</code>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => {
              if (issued) {
                void navigator.clipboard.writeText(issued.password);
                toast.success("Copied to clipboard.");
              }
            }}
          >
            <Copy className="size-3.5" /> Copy
          </Button>
        </div>
      </Dialog>

      {/* ── Delete confirmation ─────────────────────────────────────────── */}
      <Dialog
        open={pendingDelete !== null}
        onOpenChange={(o) => !o && setPendingDelete(null)}
        title="Delete this account?"
        description="This cannot be undone. The email address is freed for reuse immediately."
        footer={
          <>
            <Button variant="secondary" onClick={() => setPendingDelete(null)}>
              Cancel
            </Button>
            <Button
              variant="danger"
              loading={deleteUser.isPending}
              onClick={() => pendingDelete && deleteUser.mutate(pendingDelete)}
            >
              <Trash2 className="size-4" /> Delete permanently
            </Button>
          </>
        }
      >
        <p className="text-sm text-fg-secondary">
          <span className="font-semibold text-fg">{pendingDelete?.full_name}</span> (
          {pendingDelete?.email}) will be permanently removed. If they own any records once students
          or batches are in use, deactivating is the safer choice.
        </p>
      </Dialog>
    </>
  );
}
