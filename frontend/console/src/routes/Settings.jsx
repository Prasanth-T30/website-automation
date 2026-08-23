import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { ErrorState, LoadingState } from "@/components/ui/States";
import { settingsApi } from "@/features/settings/api";
import { ApiError } from "@/lib/api";
const FIELDS = [
  { key: "name", label: "Institute Name" },
  { key: "email", label: "Email" },
  { key: "phone", label: "Phone" },
  { key: "address", label: "Address" },
  { key: "website", label: "Website" },
  { key: "gst", label: "GST" },
];
const SETTINGS_KEY = ["settings"];
export default function Settings() {
  const queryClient = useQueryClient();
  const settings = useQuery({ queryKey: SETTINGS_KEY, queryFn: settingsApi.get });
  const [values, setValues] = useState(null);
  useEffect(() => {
    if (settings.data && values === null) {
      const { updated_at: _updated_at, ...editable } = settings.data;
      setValues(editable);
    }
  }, [settings.data, values]);
  const save = useMutation({
    mutationFn: () => settingsApi.update(values),
    onSuccess: async (updated) => {
      queryClient.setQueryData(SETTINGS_KEY, updated);
      toast.success("Institute settings saved.");
    },
    onError: (err) =>
      toast.error(err instanceof ApiError ? err.detail : "Could not save settings."),
  });
  return (
    <>
      <PageHeader
        title="Settings"
        description="General institute contact details for internal reference."
      />

      <div className="mx-auto max-w-3xl p-6">
        {settings.isPending && <LoadingState label="Loading settings…" />}

        {settings.isError && (
          <ErrorState
            description={
              settings.error instanceof ApiError
                ? settings.error.detail
                : "Could not load settings."
            }
            onRetry={() => settings.refetch()}
          />
        )}

        {values && (
          <Card>
            <CardHeader title="Institute Details" />
            <CardBody className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              {FIELDS.map((f) => (
                <Field key={f.key} label={f.label}>
                  <Input
                    value={values[f.key] ?? ""}
                    onChange={(e) => setValues((v) => ({ ...v, [f.key]: e.target.value }))}
                  />
                </Field>
              ))}
            </CardBody>
            <div className="flex justify-end gap-2 border-t border-line-subtle bg-subtle/50 px-5 py-3">
              <Button
                variant="secondary"
                onClick={() => {
                  if (!settings.data) return;
                  const { updated_at: _updated_at, ...editable } = settings.data;
                  setValues(editable);
                }}
              >
                Reset
              </Button>
              <Button loading={save.isPending} onClick={() => save.mutate()}>
                Save changes
              </Button>
            </div>
          </Card>
        )}

        <p className="mt-4 text-xs text-fg-muted">
          Looking for user accounts? Those are managed on the{" "}
          <Link
            to="/admin/users"
            className="font-semibold text-[var(--brand-text)] hover:underline"
          >
            Users
          </Link>{" "}
          screen.
        </p>
      </div>
    </>
  );
}
