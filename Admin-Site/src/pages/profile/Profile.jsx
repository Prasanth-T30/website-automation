import { FiLogOut, FiMail, FiShield, FiUser } from "react-icons/fi";

import DashboardLayout from "../../components/layout/DashboardLayout";
import { useAuth } from "../../hooks/useAuth";

const Row = ({ icon: Icon, label, value }) => (
  <div className="flex items-center justify-between gap-4 border-b border-[#EEF2F7] py-3 text-sm last:border-b-0">
    <span className="flex items-center gap-2 font-medium text-[#6B7A90]">
      <Icon size={15} className="text-[#8494A9]" />
      {label}
    </span>
    <span className="text-right font-bold text-[#0F1B2D]">{value || "-"}</span>
  </div>
);

const PERMISSIONS = [
  "View and search all internship, course, and project registrations",
  "Approve or reject registrations and trigger applicant emails",
  "Download registration data as Excel or CSV exports",
  "View dashboard analytics and registration trends",
  "Manage default approval email templates",
];

const Profile = () => {
  const { admin, logout } = useAuth();

  return (
    <DashboardLayout title="Profile">
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="glass-card p-6 lg:col-span-2">
          <div className="flex flex-wrap items-center gap-4 border-b border-[#EEF2F7] pb-5">
            <span className="flex h-16 w-16 shrink-0 items-center justify-center rounded-full bg-primary-100 text-2xl font-extrabold text-primary-600">
              {(admin?.name || "A").charAt(0).toUpperCase()}
            </span>
            <div className="min-w-0">
              <p className="truncate text-lg font-extrabold text-[#0F1B2D]">{admin?.name || "Admin"}</p>
              <p className="truncate text-sm font-medium text-[#6B7A90]">{admin?.email}</p>
              <span className="mt-1.5 inline-block rounded-full border border-[#DCE4EE] bg-[#EFF2F6] px-2.5 py-0.5 text-[11px] font-bold uppercase tracking-[.04em] text-[#5C6C81]">
                {admin?.role || "Administrator"}
              </span>
            </div>
          </div>

          <div className="pt-2">
            <h2 className="mb-1 mt-4 text-sm font-extrabold uppercase tracking-[.04em] text-[#8494A9]">Account Details</h2>
            <Row icon={FiUser} label="Full Name" value={admin?.name} />
            <Row icon={FiMail} label="Email Address" value={admin?.email} />
            <Row icon={FiShield} label="Role" value={admin?.role || "Administrator"} />
          </div>

          <button
            onClick={logout}
            className="btn-danger mt-6 w-full sm:w-auto"
          >
            <FiLogOut /> Sign Out
          </button>
        </div>

        <div className="glass-card p-6">
          <h2 className="mb-3 text-sm font-extrabold uppercase tracking-[.04em] text-[#8494A9]">Access &amp; Permissions</h2>
          <ul className="space-y-3">
            {PERMISSIONS.map((perm) => (
              <li key={perm} className="flex items-start gap-2.5 text-sm leading-5 text-[#41536B]">
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-primary-500" />
                {perm}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </DashboardLayout>
  );
};

export default Profile;
