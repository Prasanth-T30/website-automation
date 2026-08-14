import { useEffect, useState } from "react";
import { toast } from "react-toastify";

import {
  ApprovalRatioChart,
  CollegeBarChart,
  DomainBarChart,
  MonthlyTrendChart,
} from "../../components/dashboard/AnalyticsChart";
import Loader from "../../components/common/Loader";
import DashboardLayout from "../../components/layout/DashboardLayout";
import { getAnalytics } from "../../services/registrationService";

const Analytics = () => {
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const data = await getAnalytics();
        setAnalytics(data);
      } catch {
        toast.error("Failed to load analytics");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  if (loading) {
    return (
      <DashboardLayout title="Analytics">
        <Loader label="Loading analytics..." />
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout title="Analytics">
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="glass-card overflow-hidden p-5">
          <h3 className="-mx-5 -mt-5 mb-4 rounded-t-2xl bg-[#0F1B2D] px-5 py-3 text-sm font-extrabold text-white">Monthly Registrations</h3>
          <MonthlyTrendChart data={analytics?.monthly_registrations} />
        </div>
        <div className="glass-card overflow-hidden p-5">
          <h3 className="-mx-5 -mt-5 mb-4 rounded-t-2xl bg-[#0F1B2D] px-5 py-3 text-sm font-extrabold text-white">Approval Ratio</h3>
          <ApprovalRatioChart
            approved={analytics?.approval_ratio?.approved}
            rejected={analytics?.approval_ratio?.rejected}
          />
          <p className="text-center text-sm font-semibold text-[#6B7A90]">
            {analytics?.approval_ratio?.approval_ratio_percent ?? 0}% approval rate
          </p>
        </div>
        <div className="glass-card overflow-hidden p-5">
          <h3 className="-mx-5 -mt-5 mb-4 rounded-t-2xl bg-[#0F1B2D] px-5 py-3 text-sm font-extrabold text-white">Domain-wise Students</h3>
          <DomainBarChart data={analytics?.domain_wise} />
        </div>
        <div className="glass-card overflow-hidden p-5">
          <h3 className="-mx-5 -mt-5 mb-4 rounded-t-2xl bg-[#0F1B2D] px-5 py-3 text-sm font-extrabold text-white">College-wise Students</h3>
          <CollegeBarChart data={analytics?.college_wise} />
        </div>
      </div>
    </DashboardLayout>
  );
};

export default Analytics;
