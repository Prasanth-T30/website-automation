import { FiLogOut } from "react-icons/fi";
import { Link } from "react-router-dom";

import { useAuth } from "../../hooks/useAuth";
import Sidebar from "./Sidebar";

const DashboardLayout = ({ title, children }) => {
  const { admin, logout } = useAuth();

  return (
    <div className="dv-admin-shell flex min-h-screen w-full">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 flex items-center justify-between gap-3 border-b border-[#DEE7F1] bg-white/85 px-4 py-3 backdrop-blur-md sm:px-6">
          <div className="min-w-0 flex-1">
            <p className="truncate text-[11px] font-extrabold uppercase tracking-[.12em] text-[#8494A9]">DVein Admin</p>
            <h1 className="truncate text-lg font-extrabold text-[#0F1B2D]">{title}</h1>
          </div>
          <div className="flex shrink-0 items-center gap-3">
            <Link to="/profile" className="hidden max-w-[160px] text-right sm:block" title="View profile">
              <p className="truncate text-sm font-bold text-[#41536B] transition hover:text-primary-600">{admin?.name || "Admin"}</p>
              <p className="truncate text-xs font-medium text-[#8494A9]">{admin?.email}</p>
            </Link>
            <Link
              to="/profile"
              title="View profile"
              className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-primary-100 text-sm font-extrabold text-primary-600 transition hover:bg-primary-200"
            >
              {(admin?.name || "A").charAt(0).toUpperCase()}
            </Link>
            <button onClick={logout} className="shrink-0 rounded-lg p-2 text-[#8494A9] transition hover:bg-[#F2F6FB] hover:text-[#C2453F]" title="Logout">
              <FiLogOut size={18} />
            </button>
          </div>
        </header>
        <main className="min-w-0 flex-1 p-4 sm:p-6">{children}</main>
      </div>
    </div>
  );
};

export default DashboardLayout;
