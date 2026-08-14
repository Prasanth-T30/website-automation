import { useEffect, useState } from "react";
import { toast } from "react-toastify";

import DashboardCards from "../../components/dashboard/DashboardCards";
import Loader from "../../components/common/Loader";
import DashboardLayout from "../../components/layout/DashboardLayout";
import { getDashboardSummary } from "../../services/registrationService";

const Dashboard = () => {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const data = await getDashboardSummary();
        setSummary(data);
      } catch {
        toast.error("Failed to load dashboard summary");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  return (
    <DashboardLayout title="Dashboard">
      {loading ? (
        <Loader label="Loading dashboard..." />
      ) : (
        <div className="space-y-6">
          <DashboardCards summary={summary} />
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
            <div className="glass-card p-5 lg:col-span-2">
              <div className="mb-4 flex items-center justify-between">
                <div>
                  <h2 className="text-base font-extrabold text-[#0F1B2D]">Review queue</h2>
                  <p className="text-xs font-medium text-[#6B7A90]">Pending registrations that need admin verification.</p>
                </div>
                <span className="rounded-full bg-[#FDF0DC] px-3 py-1 text-xs font-bold text-[#B4741A]">{summary?.pending ?? 0} Pending</span>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-[#E7EDF5]">
                <div className="h-full rounded-full bg-gradient-to-r from-primary-500 via-accent-500 to-[#7DC244]" style={{ width: `${Math.min(((summary?.approved ?? 0) / Math.max(summary?.total_registrations ?? 1, 1)) * 100, 100)}%` }} />
              </div>
              <p className="mt-3 text-xs font-semibold text-[#8494A9]">{summary?.approved ?? 0} approved out of {summary?.total_registrations ?? 0} total registrations</p>
            </div>
            <div className="glass-card p-5">
              <h2 className="text-base font-extrabold text-[#0F1B2D]">Today</h2>
              <p className="mt-3 text-4xl font-extrabold text-primary-600">{summary?.todays_registrations ?? 0}</p>
              <p className="mt-1 text-sm font-semibold text-[#6B7A90]">new applications since midnight</p>
            </div>
          </div>
        </div>
      )}
    </DashboardLayout>
  );
};

export default Dashboard;
