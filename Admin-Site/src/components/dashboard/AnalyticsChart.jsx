import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const COLORS = ["#3569AC", "#15B5B8", "#f59e0b", "#ef4444", "#10b981", "#8b5cf6", "#ec4899", "#0ea5e9"];

export const MonthlyTrendChart = ({ data = [] }) => {
  const formatted = data.map((d) => ({ name: `${MONTH_NAMES[d.month - 1]} ${d.year}`, count: d.count }));
  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={formatted}>
        <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
        <XAxis dataKey="name" fontSize={12} />
        <YAxis allowDecimals={false} fontSize={12} />
        <Tooltip />
        <Line type="monotone" dataKey="count" stroke="#3569AC" strokeWidth={2.5} dot={{ r: 3 }} />
      </LineChart>
    </ResponsiveContainer>
  );
};

export const DomainBarChart = ({ data = [] }) => (
  <ResponsiveContainer width="100%" height={280}>
    <BarChart data={data}>
      <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
      <XAxis dataKey="domain" fontSize={11} interval={0} angle={-25} textAnchor="end" height={70} />
      <YAxis allowDecimals={false} fontSize={12} />
      <Tooltip />
      <Bar dataKey="count" radius={[6, 6, 0, 0]}>
        {data.map((_, idx) => (
          <Cell key={idx} fill={COLORS[idx % COLORS.length]} />
        ))}
      </Bar>
    </BarChart>
  </ResponsiveContainer>
);

export const ApprovalRatioChart = ({ approved = 0, rejected = 0 }) => {
  const data = [
    { name: "Approved", value: approved },
    { name: "Rejected", value: rejected },
  ];
  return (
    <ResponsiveContainer width="100%" height={240}>
      <PieChart>
        <Pie data={data} dataKey="value" nameKey="name" innerRadius={55} outerRadius={85} paddingAngle={3}>
          <Cell fill="#10b981" />
          <Cell fill="#ef4444" />
        </Pie>
        <Legend />
        <Tooltip />
      </PieChart>
    </ResponsiveContainer>
  );
};

export const CollegeBarChart = ({ data = [] }) => (
  <ResponsiveContainer width="100%" height={280}>
    <BarChart data={data} layout="vertical" margin={{ left: 40 }}>
      <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
      <XAxis type="number" allowDecimals={false} fontSize={12} />
      <YAxis type="category" dataKey="college" width={140} fontSize={11} />
      <Tooltip />
      <Bar dataKey="count" fill="#15B5B8" radius={[0, 6, 6, 0]} />
    </BarChart>
  </ResponsiveContainer>
);
