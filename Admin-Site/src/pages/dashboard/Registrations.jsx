import { useEffect, useState } from "react";
import { FiCheck, FiDownload, FiEye, FiTrash2, FiX } from "react-icons/fi";
import { Link } from "react-router-dom";
import { toast } from "react-toastify";

import Button from "../../components/common/Button";
import Input from "../../components/common/Input";
import Loader from "../../components/common/Loader";
import Modal from "../../components/common/Modal";
import Pagination from "../../components/common/Pagination";
import SearchBar from "../../components/common/SearchBar";
import Table from "../../components/common/Table";
import DashboardLayout from "../../components/layout/DashboardLayout";
import { CATEGORY_CHOICES, CATEGORY_COLORS, EMAIL_ENABLED_CATEGORIES, STATUS_COLORS } from "../../utils/constants";
import {
  approveRegistration,
  deleteRegistration,
  downloadExport,
  getRegistrations,
  rejectRegistration,
} from "../../services/registrationService";

const PAGE_SIZE = 10;

const Registrations = () => {
  const [rows, setRows] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [loading, setLoading] = useState(true);

  const [approveTarget, setApproveTarget] = useState(null);
  const [rejectTarget, setRejectTarget] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [reason, setReason] = useState("");
  const [actionLoading, setActionLoading] = useState(false);
  const [exportLoading, setExportLoading] = useState(null);

  const approveWillEmail = approveTarget ? EMAIL_ENABLED_CATEGORIES.includes(approveTarget.category) : true;

  const fetchData = async () => {
    setLoading(true);
    try {
      const res = await getRegistrations({
        search: search || undefined,
        status: statusFilter || undefined,
        category: categoryFilter || undefined,
        page,
        page_size: PAGE_SIZE,
      });
      setRows(res.data);
      setTotal(res.total);
      setTotalPages(res.total_pages);
    } catch {
      toast.error("Failed to load registrations");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, statusFilter, categoryFilter]);

  useEffect(() => {
    const timeout = setTimeout(() => {
      setPage(1);
      fetchData();
    }, 400);
    return () => clearTimeout(timeout);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search]);

  const openApprove = (reg) => {
    setApproveTarget(reg);
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
  };

  const confirmApprove = async () => {
    setActionLoading(true);
    try {
      const updated = await approveRegistration(approveTarget.id, subject, body);
      toast.success(updated?.email_sent ? "Registration approved and email sent" : "Registration approved (no email required for this category)");
      setApproveTarget(null);
      fetchData();
    } catch {
      toast.error("Failed to approve registration");
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
      await rejectRegistration(rejectTarget.id, reason);
      toast.success("Registration rejected and email sent");
      setRejectTarget(null);
      setReason("");
      fetchData();
    } catch {
      toast.error("Failed to reject registration");
    } finally {
      setActionLoading(false);
    }
  };

  const confirmDelete = async () => {
    setActionLoading(true);
    try {
      await deleteRegistration(deleteTarget.id);
      toast.success("Registration deleted");
      setDeleteTarget(null);
      fetchData();
    } catch {
      toast.error("Failed to delete registration");
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <DashboardLayout title="Registrations">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3 rounded-2xl border border-[#DEE7F1] bg-white p-3 shadow-[0_18px_46px_-36px_rgba(15,27,45,.42)]">
        <div className="flex flex-1 flex-wrap items-center gap-3">
          <SearchBar value={search} onChange={setSearch} placeholder="Search by name, email, ID, college..." />
          <select value={statusFilter} onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }} className="input-base w-auto min-w-[150px]">
            <option value="">All Status</option>
            <option value="Pending">Pending</option>
            <option value="Approved">Approved</option>
            <option value="Rejected">Rejected</option>
          </select>
          <select value={categoryFilter} onChange={(e) => { setCategoryFilter(e.target.value); setPage(1); }} className="input-base w-auto min-w-[150px]">
            <option value="">All Categories</option>
            {CATEGORY_CHOICES.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>
        <div className="flex shrink-0 gap-2">
          <Button
            variant="secondary"
            loading={exportLoading === "excel"}
            disabled={exportLoading !== null}
            onClick={async () => {
              setExportLoading("excel");
              try {
                await downloadExport("excel");
                toast.success("✓ Excel file downloaded successfully!");
              } catch (error) {
                const errorMessage = error.message || "Failed to download Excel file";
                console.error("[Excel Download Error]", errorMessage, error);
                toast.error(errorMessage);
              } finally {
                setExportLoading(null);
              }
            }}
            className="w-28"
          >
            <FiDownload /> Excel
          </Button>
          <Button
            variant="secondary"
            loading={exportLoading === "pdf"}
            disabled={exportLoading !== null}
            onClick={async () => {
              setExportLoading("pdf");
              try {
                await downloadExport("pdf");
                toast.success("✓ PDF file downloaded successfully!");
              } catch (error) {
                const errorMessage = error.message || "Failed to download PDF file";
                console.error("[PDF Download Error]", errorMessage, error);
                toast.error(errorMessage);
              } finally {
                setExportLoading(null);
              }
            }}
            className="w-28"
          >
            <FiDownload /> PDF
          </Button>
        </div>
      </div>

      {loading ? (
        <Loader label="Loading registrations..." />
      ) : (
        <>
          <Table columns={["Registration ID", "Name", "Type", "Email", "College / Company", "Category", "Domain", "Duration", "Amount", "Status", "Actions"]}>
            {rows.length === 0 && (
              <tr>
                <td colSpan={11} className="px-4 py-10 text-center text-sm font-medium text-[#8494A9]">No registrations found.</td>
              </tr>
            )}
            {rows.map((reg) => (
              <tr key={reg.id} className="hover:bg-[#F7FAFD]">
                <td className="whitespace-nowrap px-3 py-2 font-mono font-semibold text-primary-600">{reg.registration_id}</td>
                <td className="whitespace-nowrap px-3 py-2">{reg.name}</td>
                <td className="whitespace-nowrap px-3 py-2">
                  <span className={`rounded-full border px-2.5 py-1 text-[11px] font-bold ${reg.applicant_type === "professional" ? "border-[#BCE3E4] bg-[#E7F3F3] text-[#0F8F92]" : "border-[#DCE4EE] bg-[#EFF2F6] text-[#5C6C81]"}`}>
                    {reg.applicant_type === "professional" ? "Professional" : "Student"}
                  </span>
                </td>
                <td className="whitespace-nowrap px-3 py-2 text-[#6B7A90]">{reg.email}</td>
                <td className="px-3 py-2">
                  <span className="mx-auto block max-w-[110px] truncate" title={reg.college}>{reg.college}</span>
                </td>
                <td className="whitespace-nowrap px-3 py-2">
                  <span className={`rounded-full border px-2.5 py-1 text-[11px] font-medium ${CATEGORY_COLORS[reg.category] || CATEGORY_COLORS.Internship}`}>{reg.category || "Internship"}</span>
                </td>
                <td className="whitespace-nowrap px-3 py-2">{reg.domain}</td>
                <td className="whitespace-nowrap px-3 py-2">{reg.duration}</td>
                <td className="whitespace-nowrap px-3 py-2">₹{reg.amount}</td>
                <td className="whitespace-nowrap px-3 py-2">
                  <span className={`rounded-full border px-2.5 py-1 text-[11px] font-medium ${STATUS_COLORS[reg.status]}`}>{reg.status}</span>
                </td>
                <td className="whitespace-nowrap px-3 py-2">
                  <div className="flex items-center justify-center gap-1.5">
                    <Link to={`/registrations/${reg.id}`} className="rounded-lg p-1.5 text-[#8494A9] hover:bg-[#EAF2FB] hover:text-primary-600" title="View">
                      <FiEye size={15} />
                    </Link>
                    {reg.status !== "Approved" && (
                      <button onClick={() => openApprove(reg)} className="rounded-lg p-1.5 text-[#8494A9] hover:bg-[#E4F4EA] hover:text-[#2E8B57]" title="Approve">
                        <FiCheck size={15} />
                      </button>
                    )}
                    {reg.status !== "Rejected" && (
                      <button onClick={() => setRejectTarget(reg)} className="rounded-lg p-1.5 text-[#8494A9] hover:bg-[#FBE7E7] hover:text-[#C2453F]" title="Reject">
                        <FiX size={15} />
                      </button>
                    )}
                    <button onClick={() => setDeleteTarget(reg)} className="rounded-lg p-1.5 text-[#8494A9] hover:bg-[#FBE7E7] hover:text-[#C2453F]" title="Delete">
                      <FiTrash2 size={15} />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </Table>
          <p className="mt-2 text-xs font-semibold text-[#8494A9]">{total} total registrations</p>
          <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
        </>
      )}

      {/* Approve Modal */}
      <Modal
        open={!!approveTarget}
        onClose={() => setApproveTarget(null)}
        title={`Approve ${approveTarget?.registration_id || ""}`}
        maxWidth="max-w-xl"
        footer={
          <>
            <Button variant="secondary" onClick={() => setApproveTarget(null)}>Cancel</Button>
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
            <p className="text-xs font-medium text-[#8494A9]">The {approveTarget?.category || "Internship"} confirmation letter (PDF) will be generated and attached automatically.</p>
          </div>
        ) : (
          <p className="text-sm leading-6 text-[#5A6B82]">
            {approveTarget?.category || "Project"} registrations don't send an approval email or PDF — this will just
            mark <strong>{approveTarget?.registration_id}</strong> as Approved.
          </p>
        )}
      </Modal>

      {/* Reject Modal */}
      <Modal
        open={!!rejectTarget}
        onClose={() => setRejectTarget(null)}
        title={`Reject ${rejectTarget?.registration_id || ""}`}
        footer={
          <>
            <Button variant="secondary" onClick={() => setRejectTarget(null)}>Cancel</Button>
            <Button variant="danger" loading={actionLoading} onClick={confirmReject}>Send & Reject</Button>
          </>
        }
      >
        <Input as="textarea" rows={5} label="Reason for rejection" value={reason} onChange={(e) => setReason(e.target.value)} required />
      </Modal>

      {/* Delete Confirmation */}
      <Modal
        open={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        title="Delete Registration"
        footer={
          <>
            <Button variant="secondary" onClick={() => setDeleteTarget(null)}>Cancel</Button>
            <Button variant="danger" loading={actionLoading} onClick={confirmDelete}>Delete</Button>
          </>
        }
      >
        <p className="text-sm leading-6 text-[#5A6B82]">
          Are you sure you want to permanently delete registration <strong>{deleteTarget?.registration_id}</strong>? This action cannot be undone.
        </p>
      </Modal>
    </DashboardLayout>
  );
};

export default Registrations;
