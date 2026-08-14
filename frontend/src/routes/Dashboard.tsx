import { Banknote, GraduationCap, Layers, ShieldCheck, TrendingUp, Users } from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Link } from "react-router-dom";

import { MockBanner } from "@/components/MockBanner";
import { PageHeader } from "@/components/PageHeader";
import { Avatar } from "@/components/ui/Avatar";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { useAuth } from "@/features/auth/AuthProvider";
import { money } from "@/lib/format";
import {
  batchAttendanceRate,
  dashboardStats,
  domainDistribution,
  hrPerformance,
  monthlyRegistrations,
  monthlyRevenue,
} from "@/mock/data";

const CHART_COLORS = [
  "var(--color-brand-500)", "var(--color-accent-500)", "var(--color-signal-500)",
  "var(--color-warn-500)", "var(--color-danger-400)", "var(--color-brand-300)",
  "var(--color-accent-300)", "var(--color-signal-300)", "var(--color-brand-800)",
  "var(--color-accent-800)",
];

function StatTile({ icon: Icon, label, value, tone }: {
  icon: typeof Users; label: string; value: string; tone: string;
}) {
  return (
    <Card>
      <CardBody className="flex items-center gap-3">
        <div className={`flex size-10 items-center justify-center rounded-md ${tone}`}>
          <Icon className="size-5" />
        </div>
        <div>
          <p className="text-xs font-semibold text-fg-muted">{label}</p>
          <p className="text-lg font-extrabold text-fg">{value}</p>
        </div>
      </CardBody>
    </Card>
  );
}

export default function Dashboard() {
  const { user, isAdmin } = useAuth();
  const firstName = user?.full_name.split(" ")[0] ?? "there";
  const stats = dashboardStats();

  return (
    <>
      <PageHeader
        title={`Welcome back, ${firstName}`}
        description={
          isAdmin
            ? "Institute-wide overview: students, revenue and how each HR is progressing."
            : "Claim applications from the shared pool and drive your students through to completion."
        }
      />
      <MockBanner phase="Phase 6 — Analytics, HR performance and settings" />

      <div className="grid grid-cols-1 gap-4 p-6 sm:grid-cols-2 lg:grid-cols-4">
        <StatTile icon={GraduationCap} label="Total Students" value={String(stats.total_students)} tone="bg-brand-subtle text-brand" />
        <StatTile icon={Layers} label="Active Batches" value={String(stats.active_batches)} tone="bg-accent-subtle text-accent" />
        <StatTile icon={Banknote} label="Total Revenue" value={money(stats.total_revenue)} tone="bg-success-subtle text-success" />
        <StatTile icon={TrendingUp} label="Overdue" value={money(stats.overdue_amount)} tone="bg-danger-subtle text-danger" />
      </div>

      <div className="grid grid-cols-1 gap-4 px-6 pb-6 lg:grid-cols-2">
        <Card>
          <CardHeader title="Monthly Registrations" description="Trailing 7 months" />
          <CardBody className="h-64 !p-4">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={monthlyRegistrations}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" />
                <XAxis dataKey="month" tick={{ fontSize: 12, fill: "var(--text-muted)" }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 12, fill: "var(--text-muted)" }} axisLine={false} tickLine={false} width={28} />
                <Tooltip
                  contentStyle={{ background: "var(--bg-surface)", border: "1px solid var(--border-default)", borderRadius: 8, fontSize: 12 }}
                />
                <Line type="monotone" dataKey="count" stroke="var(--color-brand-500)" strokeWidth={2.5} dot={{ r: 3 }} />
              </LineChart>
            </ResponsiveContainer>
          </CardBody>
        </Card>

        <Card>
          <CardHeader title="Revenue Analytics" description="₹ thousands, per month" />
          <CardBody className="h-64 !p-4">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={monthlyRevenue}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" />
                <XAxis dataKey="month" tick={{ fontSize: 12, fill: "var(--text-muted)" }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 12, fill: "var(--text-muted)" }} axisLine={false} tickLine={false} width={28} />
                <Tooltip
                  contentStyle={{ background: "var(--bg-surface)", border: "1px solid var(--border-default)", borderRadius: 8, fontSize: 12 }}
                  formatter={(v: number) => [`₹${v}k`, "Revenue"]}
                />
                <Bar dataKey="amount" fill="var(--color-accent-500)" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardBody>
        </Card>

        <Card>
          <CardHeader title="Domain-wise Students" description="Live distribution across active domains" />
          <CardBody className="flex h-64 items-center !p-4">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={domainDistribution}
                  dataKey="count"
                  nameKey="domain"
                  innerRadius={45}
                  outerRadius={80}
                  paddingAngle={2}
                >
                  {domainDistribution.map((d, i) => (
                    <Cell key={d.domain} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{ background: "var(--bg-surface)", border: "1px solid var(--border-default)", borderRadius: 8, fontSize: 12 }}
                />
              </PieChart>
            </ResponsiveContainer>
            <ul className="flex shrink-0 flex-col gap-1.5 pl-2 text-xs">
              {domainDistribution.map((d, i) => (
                <li key={d.domain} className="flex items-center gap-1.5">
                  <span
                    className="size-2 shrink-0 rounded-full"
                    style={{ background: CHART_COLORS[i % CHART_COLORS.length] }}
                  />
                  <span className="text-fg-secondary">{d.domain}</span>
                  <span className="ml-auto font-semibold text-fg">{d.count}</span>
                </li>
              ))}
            </ul>
          </CardBody>
        </Card>

        <Card>
          <CardHeader title="Batch Attendance" description="Present % over the last 7 sessions" />
          <CardBody className="h-64 !p-4">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={batchAttendanceRate} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" horizontal={false} />
                <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 12, fill: "var(--text-muted)" }} axisLine={false} tickLine={false} />
                <YAxis type="category" dataKey="code" tick={{ fontSize: 12, fill: "var(--text-muted)" }} axisLine={false} tickLine={false} width={64} />
                <Tooltip
                  contentStyle={{ background: "var(--bg-surface)", border: "1px solid var(--border-default)", borderRadius: 8, fontSize: 12 }}
                  formatter={(v: number) => [`${v}%`, "Present"]}
                />
                <Bar dataKey="pct" fill="var(--color-signal-500)" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardBody>
        </Card>
      </div>

      {isAdmin && (
        <div className="px-6 pb-6">
          <Card>
            <CardHeader
              title="HR Performance"
              description="Applications claimed, converted, and revenue attributed to each HR."
            />
            <CardBody className="!p-0">
              <div className="scroll-x">
                <table className="w-full min-w-[560px] text-sm">
                  <thead>
                    <tr className="border-b border-line-subtle bg-subtle/60 text-left">
                      {["HR", "Claimed", "Converted", "Conversion", "Active Students", "Revenue"].map((h) => (
                        <th key={h} className="px-4 py-2.5 text-xs font-bold tracking-wide text-fg-muted uppercase">
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {hrPerformance.map((row) => (
                      <tr key={row.hr.id} className="border-b border-line-subtle last:border-0">
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-2.5">
                            <Avatar name={row.hr.name} size="sm" />
                            <span className="font-medium text-fg">{row.hr.name}</span>
                          </div>
                        </td>
                        <td className="px-4 py-3 text-fg-secondary">{row.claimed}</td>
                        <td className="px-4 py-3 text-fg-secondary">{row.converted}</td>
                        <td className="px-4 py-3 font-semibold text-fg">{row.conversionRate}%</td>
                        <td className="px-4 py-3 text-fg-secondary">{row.activeStudents}</td>
                        <td className="px-4 py-3 font-semibold text-fg">{money(row.revenue)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardBody>
          </Card>
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 px-6 pb-6 sm:grid-cols-2">
        <Card>
          <CardBody className="flex flex-col gap-2">
            <ShieldCheck className="size-5 text-success" aria-hidden />
            <h2 className="text-sm font-bold text-fg">Signed in</h2>
            <p className="text-xs text-fg-muted">
              {user?.email} · {isAdmin ? "Administrator" : "HR"}
            </p>
          </CardBody>
        </Card>

        {isAdmin && (
          <Card>
            <CardBody className="flex flex-col gap-2">
              <Users className="size-5 text-brand" aria-hidden />
              <h2 className="text-sm font-bold text-fg">Manage the team</h2>
              <p className="text-xs text-fg-muted">
                Add HR accounts, reset passwords, deactivate people who leave.
              </p>
              <Link
                to="/admin/users"
                className="mt-1 text-xs font-semibold text-[var(--brand-text)] hover:underline"
              >
                Open Users →
              </Link>
            </CardBody>
          </Card>
        )}
      </div>
    </>
  );
}
