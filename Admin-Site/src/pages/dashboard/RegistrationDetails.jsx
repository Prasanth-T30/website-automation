import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { FiArrowLeft, FiCheck, FiDownload, FiX, FiZoomIn } from "react-icons/fi";
import { Link, useParams } from "react-router-dom";
import { toast } from "react-toastify";

import Button from "../../components/common/Button";
import Input from "../../components/common/Input";
import Loader from "../../components/common/Loader";
import Modal from "../../components/common/Modal";
import DashboardLayout from "../../components/layout/DashboardLayout";
import { UPLOADS_BASE_URL } from "../../config/config";
import { CATEGORY_COLORS, EMAIL_ENABLED_CATEGORIES, STATUS_COLORS } from "../../utils/constants";
import { approveRegistration, getRegistration, offerLetterUrl, rejectRegistration, saveApprovalEmail } from "../../services/registrationService";

const Row = ({ label, value }) => (
  <div className="flex items-center justify-between gap-4 border-b border-[#EEF2F7] py-2.5 text-sm">
    <span className="font-medium text-[#6B7A90]">{label}</span>
    <span className="text-right font-bold text-[#0F1B2D]">{value || "-"}</span>
  </div>
);

const ImageLightbox = ({ src, onClose }) => (
  <AnimatePresence>
    {src && (
      <motion.div
        className="fixed inset-0 z-[60] flex items-center justify-center bg-[#0F1B2D]/85 p-4 backdrop-blur-sm"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onClose}
      >
        <motion.div
          className="relative max-h-[90vh] max-w-[90vw]"
          initial={{ scale: 0.92, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.92, opacity: 0 }}
          onClick={(e) => e.stopPropagation()}
        >
          <button
            onClick={onClose}
            className="absolute -top-3 -right-3 flex h-9 w-9 items-center justify-center rounded-full bg-white text-[#0F1B2D] shadow-lg transition hover:bg-[#F2F6FB]"
            title="Close"
          >
            <FiX size={18} />
          </button>
          <img src={src} alt="Payment proof enlarged" className="max-h-[90vh] max-w-[90vw] rounded-[14px] object-contain shadow-[0_24px_60px_-20px_rgba(0,0,0,.6)]" />
        </motion.div>
      </motion.div>
    )}
  </AnimatePresence>
);

const RegistrationDetails = () => {
  const { id } = useParams();
  const [reg, setReg] = useState(null);
  const [loading, setLoading] = useState(true);
  const [lightboxSrc, setLightboxSrc] = useState(null);

  const [approveOpen, setApproveOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [rejectOpen, setRejectOpen] = useState(false);
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [editSubject, setEditSubject] = useState("");
  const [editBody, setEditBody] = useState("");
  const [reason, setReason] = useState("");
  const [actionLoading, setActionLoading] = useState(false);

  const fetchData = async () => {
    try {
      const data = await getRegistration(id);
      setReg(data);
    } catch {
      toast.error("Failed to load registration details");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const isProfessional = reg?.applicant_type === "professional";
  const approveWillEmail = reg ? EMAIL_ENABLED_CATEGORIES.includes(reg.category || "Internship") : true;

  const openApprove = () => {
    const category = reg.category || "Internship";
    if (EMAIL_ENABLED_CATEGORIES.includes(category)) {
      setSubject(`${category} Registration Approved`);
      setBody(
        `Congratulations! Your ${category.toLowerCase()} registration has been approved.\n\nRegistration ID: ${reg.registration_id}\nCategory: ${category}\nDomain: ${reg.domain}\nDuration: ${reg.duration}\nStart Date: ${reg.start_date}\nEnd Date: ${reg.end_date}\n\nPlease find the attached ${category} confirmation letter.`
      );
    } else {
      setSubject("");
      setBody("");
    }
    setApproveOpen(true);
  };

  const openEditApproval = () => {
    const category = reg.category || "Internship";
    const defaultSubject = reg.approval_email_subject || `${category} Registration Approved`;
    const defaultBody = reg.approval_email_body || `Congratulations! Your ${category.toLowerCase()} registration has been approved.\n\nRegistration ID: ${reg.registration_id}\nCategory: ${category}\nDomain: ${reg.domain}\nDuration: ${reg.duration}\nStart Date: ${reg.start_date}\nEnd Date: ${reg.end_date}\n\nPlease find the attached ${category} confirmation letter.`;
    setEditSubject(defaultSubject);
    setEditBody(defaultBody);
    setEditOpen(true);
  };

  const confirmApprove = async () => {
    setActionLoading(true);
    try {
      const updated = await approveRegistration(reg.id, subject, body);
      toast.success(updated?.email_sent ? "Registration approved and email sent" : "Registration approved (no email required for this category)");
      setApproveOpen(false);
      fetchData();
    } catch {
      toast.error("Failed to approve registration");
    } finally {
      setActionLoading(false);
    }
  };

  const confirmSaveApprovalEmail = async () => {
    setActionLoading(true);
    try {
      await saveApprovalEmail(reg.id, editSubject, editBody);
      toast.success("Approval email and offer letter updated");
      setEditOpen(false);
      fetchData();
    } catch {
      toast.error("Failed to update approval email");
    } finally {
      setActionLoading(false);
    }
  };

  const confirmReject = async () => {
    if (!reason.trim()) {
      toast.error("Please provide a rejection reason");
      return;
    }
    setActionLoading(true);
    try {
      await rejectRegistration(reg.id, reason);
      toast.success("Registration rejected and email sent");
      setRejectOpen(false);
      setReason("");
      fetchData();
    } catch {
      toast.error("Failed to reject registration");
    } finally {
      setActionLoading(false);
    }
  };

  const screenshotUrl = reg?.payment_screenshot ? `${UPLOADS_BASE_URL}/uploads/payments/${reg.payment_screenshot}` : null;

  return (
    <DashboardLayout title="Registration Details">
      <Link to="/registrations" className="mb-4 inline-flex items-center gap-1 text-sm font-bold text-primary-600 hover:underline">
        <FiArrowLeft /> Back to Registrations
      </Link>

      {loading ? (
        <Loader />
      ) : !reg ? (
        <p className="text-sm font-medium text-[#8494A9]">Registration not found.</p>
      ) : (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <div className="glass-card p-6 lg:col-span-2">
            <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="font-mono text-xs font-semibold text-primary-600">{reg.registration_id}</p>
                <h2 className="mt-1 text-xl font-extrabold text-[#0F1B2D]">{reg.name}</h2>
                <p className="mt-1 text-sm font-medium text-[#6B7A90]">{reg.email}</p>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <span className={`rounded-full border px-3 py-1 text-xs font-bold ${isProfessional ? "border-[#BCE3E4] bg-[#E7F3F3] text-[#0F8F92]" : "border-[#DCE4EE] bg-[#EFF2F6] text-[#5C6C81]"}`}>
                  {isProfessional ? "Professional" : "Student"}
                </span>
                <span className={`rounded-full border px-3 py-1 text-xs font-bold ${CATEGORY_COLORS[reg.category] || CATEGORY_COLORS.Internship}`}>{reg.category || "Internship"}</span>
                <span className={`rounded-full border px-3 py-1 text-xs font-bold ${STATUS_COLORS[reg.status]}`}>{reg.status}</span>
              </div>
            </div>

            <div className="grid grid-cols-1 gap-x-8 md:grid-cols-2">
              <Row label="Phone" value={reg.phone} />
              <Row label="Place" value={reg.place} />
              <Row label={isProfessional ? "Company" : "College"} value={reg.college} />
              <Row label={isProfessional ? "Designation" : "Department"} value={reg.department} />
              <Row label={isProfessional ? "Experience" : "Year"} value={reg.year} />
              <Row label="Domain" value={reg.domain} />
              <Row label="Duration" value={reg.duration} />
              <Row label="Start Date" value={reg.start_date} />
              <Row label="End Date" value={reg.end_date} />
              <Row label="Amount Paid" value={`Rs. ${reg.amount}`} />
              <Row label="Transaction ID" value={reg.transaction_id} />
              <Row label="Submitted On" value={new Date(reg.created_at).toLocaleString()} />
            </div>

            {reg.status === "Approved" && (
              <div className="mt-5 flex flex-wrap gap-3">
                <a href={offerLetterUrl(reg.id)} target="_blank" rel="noreferrer" className="btn-primary inline-flex">
                  <FiDownload /> Download Offer Letter
                </a>
                <button type="button" onClick={openEditApproval} className="btn-secondary inline-flex">
                  Edit
                </button>
              </div>
            )}

            <div className="mt-6 flex flex-wrap justify-center gap-3 border-t border-[#EEF2F7] pt-5">
              {reg.status !== "Approved" && (
                <Button variant="success" onClick={openApprove} className="w-40">
                  <FiCheck /> Accept
                </Button>
              )}
              {reg.status !== "Rejected" && (
                <Button variant="danger" onClick={() => setRejectOpen(true)} className="w-40">
                  <FiX /> Reject
                </Button>
              )}
            </div>
          </div>

          <div className="glass-card p-6">
            <h3 className="mb-3 text-sm font-extrabold text-[#0F1B2D]">Payment Screenshot</h3>
            {screenshotUrl ? (
              <>
                <button
                  type="button"
                  onClick={() => setLightboxSrc(screenshotUrl)}
                  className="group relative block w-full overflow-hidden rounded-[14px] border border-[#DEE7F1]"
                  title="Click to enlarge"
                >
                  <img src={screenshotUrl} alt="Payment proof" className="w-full object-cover transition group-hover:brightness-90" />
                  <span className="absolute inset-0 flex items-center justify-center bg-[#0F1B2D]/0 text-white opacity-0 transition group-hover:bg-[#0F1B2D]/30 group-hover:opacity-100">
                    <FiZoomIn size={22} />
                  </span>
                </button>
                <a href={screenshotUrl} download className="btn-secondary mt-3 w-full">
                  <FiDownload /> Download Screenshot
                </a>
              </>
            ) : (
              <p className="text-sm font-medium text-[#8494A9]">No screenshot uploaded.</p>
            )}
          </div>
        </div>
      )}

      <ImageLightbox src={lightboxSrc} onClose={() => setLightboxSrc(null)} />

      {/* Approve Modal */}
      <Modal
        open={approveOpen}
        onClose={() => setApproveOpen(false)}
        title={`Approve ${reg?.registration_id || ""}`}
        maxWidth="max-w-xl"
        footer={
          <>
            <Button variant="secondary" onClick={() => setApproveOpen(false)}>Cancel</Button>
            <Button variant="success" loading={actionLoading} onClick={confirmApprove}>
              {approveWillEmail ? "Send & Approve" : "Approve"}
            </Button>
          </>
        }
      >
        {approveWillEmail ? (
          <div className="space-y-4">
            <Input label="Email Subject" value={subject} onChange={(e) => setSubject(e.target.value)} />
            <Input as="textarea" rows={12} label="Email Content" value={body} onChange={(e) => setBody(e.target.value)} />
            <p className="text-xs font-medium text-[#8494A9]">The {reg?.category || "Internship"} confirmation letter (PDF) will be generated and attached automatically.</p>
          </div>
        ) : (
          <p className="text-sm leading-6 text-[#5A6B82]">
            {reg?.category || "Project"} registrations don't send an approval email or PDF — this will just
            mark <strong>{reg?.registration_id}</strong> as Approved.
          </p>
        )}
      </Modal>

      {/* Edit Approval Message Modal */}
      <Modal
        open={editOpen}
        onClose={() => setEditOpen(false)}
        title={`Edit approval message for ${reg?.registration_id || ""}`}
        maxWidth="max-w-xl"
        footer={
          <>
            <Button variant="secondary" onClick={() => setEditOpen(false)}>Cancel</Button>
            <Button variant="success" loading={actionLoading} onClick={confirmSaveApprovalEmail}>Save</Button>
          </>
        }
      >
        <div className="space-y-4">
          <Input label="Email Subject" value={editSubject} onChange={(e) => setEditSubject(e.target.value)} />
          <Input as="textarea" rows={12} label="Email Content" value={editBody} onChange={(e) => setEditBody(e.target.value)} />
          <p className="text-xs font-medium text-[#8494A9]">This update changes both the stored approval email text and the generated offer-letter PDF.</p>
        </div>
      </Modal>

      {/* Reject Modal */}
      <Modal
        open={rejectOpen}
        onClose={() => setRejectOpen(false)}
        title={`Reject ${reg?.registration_id || ""}`}
        footer={
          <>
            <Button variant="secondary" onClick={() => setRejectOpen(false)}>Cancel</Button>
            <Button variant="danger" loading={actionLoading} onClick={confirmReject}>Send & Reject</Button>
          </>
        }
      >
        <Input as="textarea" rows={5} label="Reason for rejection" value={reason} onChange={(e) => setReason(e.target.value)} required />
      </Modal>
    </DashboardLayout>
  );
};

export default RegistrationDetails;
