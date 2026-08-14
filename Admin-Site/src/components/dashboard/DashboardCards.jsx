import { FiCheckCircle, FiClock, FiTrendingUp, FiUsers, FiXCircle } from "react-icons/fi";

const CARD_CONFIG = [
  { key: "total_registrations", label: "Total Registrations", icon: FiUsers, color: "from-primary-500 to-primary-600" },
  { key: "pending", label: "Pending", icon: FiClock, color: "from-amber-400 to-amber-500" },
  { key: "approved", label: "Approved", icon: FiCheckCircle, color: "from-emerald-400 to-emerald-500" },
  { key: "rejected", label: "Rejected", icon: FiXCircle, color: "from-red-400 to-red-500" },
  { key: "todays_registrations", label: "Today's Registrations", icon: FiTrendingUp, color: "from-accent-400 to-accent-500" },
];

const DashboardCards = ({ summary }) => (
  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
    {CARD_CONFIG.map(({ key, label, icon: Icon, color }) => (
      <div key={key} className="glass-card p-5" style={{ animation: "dvRise .34s cubic-bezier(.2,.7,.3,1) both" }}>
        <div className={`mb-4 flex h-10 w-10 items-center justify-center rounded-[11px] bg-gradient-to-br ${color} text-white`}>
          <Icon size={18} />
        </div>
        <p className="text-2xl font-extrabold text-[#0F1B2D]">{summary?.[key] ?? 0}</p>
        <p className="text-sm font-semibold text-[#6B7A90]">{label}</p>
      </div>
    ))}
  </div>
);

export default DashboardCards;
