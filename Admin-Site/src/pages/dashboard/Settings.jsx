import { useEffect, useState } from "react";
import { FiPlus, FiTrash2 } from "react-icons/fi";
import { toast } from "react-toastify";

import Button from "../../components/common/Button";
import Input from "../../components/common/Input";
import DashboardLayout from "../../components/layout/DashboardLayout";
import api from "../../services/api";

const EXTRA_TEMPLATES_KEY = "dvein_extra_email_templates";

const DEFAULT_SUBJECT = "{Category} Registration Approved";
const DEFAULT_BODY =
  "Dear {Student Name},\n\nCongratulations! Your {Category} registration has been approved.\n\nRegistration ID: {Registration ID}\nCategory: {Category}\nDomain: {Domain}\nDuration: {Duration}\nStart Date: {Start Date}\nEnd Date: {End Date}\n\nPlease find the attached {Category} confirmation letter.\n\nThank you.\nTraining Team\n\nNote: Project category registrations do not receive an approval email.";

const loadExtraTemplates = () => {
  try {
    const raw = localStorage.getItem(EXTRA_TEMPLATES_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
};

const EmailTemplateCard = ({ name, onNameChange, subject, onSubjectChange, body, onBodyChange, description, saving, onSave, onDelete, locked }) => (
  <div className="glass-card p-6">
    <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
      <div className="min-w-0 flex-1">
        {locked ? (
          <h2 className="text-base font-extrabold text-[#0F1B2D]">{name}</h2>
        ) : (
          <Input
            label="Template Name"
            value={name}
            onChange={(e) => onNameChange(e.target.value)}
            placeholder="e.g. Rejection Email, Reminder Email..."
          />
        )}
        {description && <p className="mt-1 text-sm font-medium text-[#6B7A90]">{description}</p>}
      </div>
      {!locked && (
        <button
          onClick={onDelete}
          className="shrink-0 rounded-lg p-2 text-[#8494A9] transition hover:bg-[#FBE7E7] hover:text-[#C2453F]"
          title="Delete template"
        >
          <FiTrash2 size={16} />
        </button>
      )}
    </div>
    <div className="space-y-4">
      <Input label="Subject" value={subject} onChange={(e) => onSubjectChange(e.target.value)} />
      <Input as="textarea" rows={10} label="Body" value={body} onChange={(e) => onBodyChange(e.target.value)} />
      <Button onClick={onSave} loading={saving}>Save Template</Button>
    </div>
  </div>
);

const Settings = () => {
  const [approvalSubject, setApprovalSubject] = useState(DEFAULT_SUBJECT);
  const [approvalBody, setApprovalBody] = useState(DEFAULT_BODY);
  const [savingDefault, setSavingDefault] = useState(false);

  const [extraTemplates, setExtraTemplates] = useState(loadExtraTemplates);
  const [savingId, setSavingId] = useState(null);

  useEffect(() => {
    localStorage.setItem(EXTRA_TEMPLATES_KEY, JSON.stringify(extraTemplates));
  }, [extraTemplates]);

  const saveDefault = async () => {
    setSavingDefault(true);
    try {
      await api.put("/settings/approval_email_template", { subject: approvalSubject, body: approvalBody });
      toast.success("Default template saved");
    } catch {
      toast.error("Failed to save settings");
    } finally {
      setSavingDefault(false);
    }
  };

  const addTemplate = () => {
    const id = `tpl_${Date.now()}`;
    setExtraTemplates((prev) => [
      ...prev,
      { id, name: "New Template", subject: "", body: "" },
    ]);
  };

  const updateTemplate = (id, field, value) => {
    setExtraTemplates((prev) => prev.map((t) => (t.id === id ? { ...t, [field]: value } : t)));
  };

  const deleteTemplate = (id) => {
    setExtraTemplates((prev) => prev.filter((t) => t.id !== id));
    toast.success("Template removed");
  };

  const saveTemplate = async (id) => {
    setSavingId(id);
    try {
      // These extra formats aren't backed by a named-template endpoint on the
      // API yet, so they're persisted locally to this browser for now — they
      // stay available across reloads and are ready to wire up to a real
      // endpoint (e.g. PUT /settings/email_templates/:id) once one exists.
      localStorage.setItem(EXTRA_TEMPLATES_KEY, JSON.stringify(extraTemplates));
      toast.success("Template saved on this device");
    } finally {
      setSavingId(null);
    }
  };

  return (
    <DashboardLayout title="Settings">
      <div className="mx-auto max-w-2xl space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-base font-extrabold text-[#0F1B2D]">Email Templates</h1>
            <p className="text-sm font-medium text-[#6B7A90]">Manage the emails sent to applicants for different outcomes.</p>
          </div>
          <Button variant="secondary" onClick={addTemplate}>
            <FiPlus /> Add Template
          </Button>
        </div>

        <EmailTemplateCard
          locked
          name="Default Approval Email Template"
          description="Used when approving Internship and Course registrations."
          subject={approvalSubject}
          onSubjectChange={setApprovalSubject}
          body={approvalBody}
          onBodyChange={setApprovalBody}
          saving={savingDefault}
          onSave={saveDefault}
        />

        {extraTemplates.map((t) => (
          <EmailTemplateCard
            key={t.id}
            name={t.name}
            onNameChange={(v) => updateTemplate(t.id, "name", v)}
            subject={t.subject}
            onSubjectChange={(v) => updateTemplate(t.id, "subject", v)}
            body={t.body}
            onBodyChange={(v) => updateTemplate(t.id, "body", v)}
            saving={savingId === t.id}
            onSave={() => saveTemplate(t.id)}
            onDelete={() => deleteTemplate(t.id)}
          />
        ))}

        {extraTemplates.length === 0 && (
          <p className="text-center text-sm font-medium text-[#8494A9]">
            No extra templates yet. Use "Add Template" to create additional email formats (e.g. rejection notices, reminders).
          </p>
        )}
      </div>
    </DashboardLayout>
  );
};

export default Settings;
