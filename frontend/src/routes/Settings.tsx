import { useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";

import { MockBanner } from "@/components/MockBanner";
import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";

const FIELDS: { key: string; label: string; value: string }[] = [
  { key: "name", label: "Institute Name", value: "Dvein Innovations" },
  { key: "email", label: "Email", value: "admin@dvein.in" },
  { key: "phone", label: "Phone", value: "+91 98765 43210" },
  { key: "address", label: "Address", value: "Coimbatore, Tamil Nadu" },
  { key: "website", label: "Website", value: "www.dvein.in" },
  { key: "gst", label: "GST", value: "33AAACD1234F1Z5" },
];

export default function Settings() {
  const [values, setValues] = useState(() => Object.fromEntries(FIELDS.map((f) => [f.key, f.value])));

  return (
    <>
      <PageHeader
        title="Settings"
        description="Institute details shown on receipts, certificates and exported documents."
      />
      <MockBanner phase="Phase 6 — Analytics, HR performance and settings" />

      <div className="mx-auto max-w-3xl p-6">
        <Card>
          <CardHeader title="Institute Details" />
          <CardBody className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {FIELDS.map((f) => (
              <Field key={f.key} label={f.label}>
                <Input
                  value={values[f.key]}
                  onChange={(e) => setValues((v) => ({ ...v, [f.key]: e.target.value }))}
                />
              </Field>
            ))}
          </CardBody>
          <div className="flex justify-end gap-2 border-t border-line-subtle bg-subtle/50 px-5 py-3">
            <Button
              variant="secondary"
              onClick={() => setValues(Object.fromEntries(FIELDS.map((f) => [f.key, f.value])))}
            >
              Reset
            </Button>
            <Button onClick={() => toast.success("Saved — persists once Phase 6 lands.")}>
              Save changes
            </Button>
          </div>
        </Card>

        <p className="mt-4 text-xs text-fg-muted">
          Looking for user accounts? Those are managed on the{" "}
          <Link to="/admin/users" className="font-semibold text-[var(--brand-text)] hover:underline">
            Users
          </Link>{" "}
          screen, which is real and already wired to the backend.
        </p>
      </div>
    </>
  );
}
