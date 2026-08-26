import { useQuery } from "@tanstack/react-query";
import {
  Award,
  Banknote,
  Bell,
  CalendarCheck,
  FileText,
  GraduationCap,
  LayoutDashboard,
  Layers,
  Moon,
  Search,
  Settings,
  Sun,
  UserCog,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { applicationsApi } from "@/features/applications/api";
import { useAuth } from "@/features/auth/AuthProvider";
import { batchesApi } from "@/features/batches/api";
import { notificationsApi } from "@/features/notifications/api";
import { paymentsApi } from "@/features/payments/api";
import { reportsApi } from "@/features/reports/api";
import { studentsApi } from "@/features/students/api";
import { usersApi } from "@/features/users/api";
import { cn } from "@/lib/cn";
import { useTheme } from "@/lib/theme";
import { initialsOf } from "./ui/Avatar";

/**
 * @typedef {"applications" | "students" | "batches" | "payments" | "reports" | "users"} CountKey
 *   Which list a sub-tab shows a count for. Keys match the routes' own query
 *   keys, so the badge is served from the cache the destination already fills.
 *
 * @typedef {object} NavItem
 * @property {string} to
 * @property {string} label
 * @property {import("react").ComponentType<{ className?: string }>} icon
 * @property {CountKey} [count]
 *
 * @typedef {object} NavGroup
 * @property {string} key
 * @property {string} label
 * @property {boolean} [adminOnly]  Admin manages the HR team and institute
 *   config — HRs never need these.
 * @property {NavItem[]} items  Non-empty: a group's first item is where its
 *   top-level tab navigates to.
 */

/* Eleven flat tabs made every screen look equally important. Grouping them by
   the job being done puts one row of six at the top and moves the sibling
   screens into a second row that only appears where there's a choice to make. */
/** @type {NavGroup[]} */
const GROUPS = [
  {
    key: "overview",
    label: "Overview",
    items: [{ to: "/", label: "Dashboard", icon: LayoutDashboard }],
  },
  {
    key: "admissions",
    label: "Admissions",
    items: [
      { to: "/applications", label: "Applications", icon: FileText, count: "applications" },
    ],
  },
  {
    key: "training",
    label: "Training",
    items: [
      { to: "/students", label: "Students", icon: GraduationCap, count: "students" },
      { to: "/batches", label: "Batches", icon: Layers, count: "batches" },
      { to: "/attendance", label: "Attendance", icon: CalendarCheck },
    ],
  },
  {
    key: "finance",
    label: "Finance",
    items: [
      { to: "/payments", label: "Payments", icon: Banknote, count: "payments" },
      { to: "/reports", label: "Documents", icon: Award, count: "reports" },
    ],
  },
  {
    key: "alerts",
    label: "Alerts",
    items: [{ to: "/notifications", label: "Notifications", icon: Bell }],
  },
  {
    key: "admin",
    label: "Admin",
    adminOnly: true,
    items: [
      { to: "/admin/users", label: "Users", icon: UserCog, count: "users" },
      { to: "/settings", label: "Settings", icon: Settings },
    ],
  },
];
function isRouteActive(pathname, to) {
  return to === "/" ? pathname === "/" : pathname === to || pathname.startsWith(`${to}/`);
}
/** Counts for the open group only — a group the user isn't looking at costs
 * no request, and the ones that do fire share the destination route's key. */
function useGroupCounts(group, isAdmin) {
  const wants = (key) => group?.items.some((i) => i.count === key) ?? false;
  const staleTime = 60_000;
  const students = useQuery({
    queryKey: ["students"],
    queryFn: () => studentsApi.list(),
    enabled: wants("students"),
    staleTime,
  });
  const batches = useQuery({
    queryKey: ["batches"],
    queryFn: () => batchesApi.list(),
    enabled: wants("batches"),
    staleTime,
  });
  const applications = useQuery({
    queryKey: ["applications"],
    queryFn: () => applicationsApi.list(),
    enabled: wants("applications"),
    staleTime,
  });
  const payments = useQuery({
    queryKey: ["payments", { mine: !isAdmin }],
    queryFn: () => paymentsApi.list({ mine: !isAdmin }),
    enabled: wants("payments"),
    staleTime,
  });
  const reports = useQuery({
    queryKey: ["reports"],
    queryFn: () => reportsApi.list(),
    enabled: wants("reports"),
    staleTime,
  });
  const users = useQuery({
    queryKey: ["admin", "users"],
    queryFn: usersApi.list,
    enabled: wants("users") && isAdmin,
    staleTime,
  });
  return {
    applications: applications.data?.length,
    students: students.data?.length,
    batches: batches.data?.length,
    payments: payments.data?.length,
    reports: reports.data?.length,
    users: users.data?.length,
  };
}
function GroupTab({ group, active }) {
  return (
    <NavLink
      to={group.items[0].to}
      className={cn(
        "relative shrink-0 px-4.5 pt-4 pb-3.5 text-[13px] tracking-tight transition-colors",
        active ? "font-bold text-fg" : "font-medium text-fg-secondary hover:text-fg",
      )}
    >
      {group.label}
      <span
        className={cn(
          "absolute inset-x-3.5 bottom-0 h-[2.5px] rounded-full transition-opacity",
          active ? "bg-gradient-to-r from-brand to-accent opacity-100" : "opacity-0",
        )}
      />
    </NavLink>
  );
}
function SubTab({ item, active, count }) {
  return (
    <NavLink
      to={item.to}
      className={cn(
        "flex h-8.5 shrink-0 items-center gap-1.75 rounded-[10px] border px-3.5 text-xs font-semibold transition-all duration-200",
        active
          ? "border-transparent bg-gradient-to-br from-brand to-brand-hover text-on-brand shadow-[0_10px_18px_-12px_var(--brand)]"
          : "border-line bg-surface text-fg-secondary hover:border-line-strong hover:text-fg",
      )}
    >
      {item.label}
      {count !== undefined && (
        <span
          className={cn(
            "rounded-md px-1.75 py-px text-[10px] font-bold tabular-nums",
            active ? "bg-white/24 text-on-brand" : "bg-inset text-fg-muted",
          )}
        >
          {count}
        </span>
      )}
    </NavLink>
  );
}
/** Closes the panel on outside click or Escape — shared by the three header popovers. */
function useDismiss(open, onClose) {
  const ref = useRef(null);
  useEffect(() => {
    if (!open) return;
    function onPointerDown(e) {
      if (ref.current && !ref.current.contains(e.target)) onClose();
    }
    function onKeyDown(e) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open, onClose]);
  return ref;
}
function SearchBox() {
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const ref = useDismiss(open, () => setOpen(false));
  const q = query.trim().toLowerCase();
  const students = useQuery({
    queryKey: ["students"],
    queryFn: () => studentsApi.list(),
    enabled: q.length > 0,
    staleTime: 60_000,
  });
  const applications = useQuery({
    queryKey: ["applications"],
    queryFn: () => applicationsApi.list(),
    enabled: q.length > 0,
    staleTime: 60_000,
  });
  const results = useMemo(() => {
    if (!q) return [];
    const studentHits = (students.data ?? [])
      .filter((s) => `${s.name} ${s.email} ${s.college}`.toLowerCase().includes(q))
      .slice(0, 3)
      .map((s) => ({
        key: `s-${s.id}`,
        initials: initialsOf(s.name),
        title: s.name,
        sub: s.domain,
        kind: "Student",
        go: () => navigate("/students"),
      }));
    const appHits = (applications.data ?? [])
      .filter((a) => `${a.name} ${a.email} ${a.college}`.toLowerCase().includes(q))
      .slice(0, 3)
      .map((a) => ({
        key: `a-${a.id}`,
        initials: initialsOf(a.name),
        title: a.name,
        sub: `${a.domain} · ${a.status}`,
        kind: "Application",
        go: () => navigate("/applications"),
      }));
    return [...studentHits, ...appHits];
  }, [q, students.data, applications.data, navigate]);
  return (
    <div ref={ref} className="relative max-w-md flex-1">
      <Search
        className="pointer-events-none absolute top-1/2 left-3 size-3.5 -translate-y-1/2 text-chrome-text"
        aria-hidden
      />
      <input
        value={query}
        onChange={(e) => {
          setQuery(e.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        placeholder="Search students, applications…"
        className="h-9 w-full rounded-md border border-white/10 bg-white/[0.06] pr-3 pl-8 text-[12.5px] font-medium text-white outline-none placeholder:text-chrome-text focus:border-accent-400/60 focus:bg-white/[0.11]"
      />
      {open && q.length > 0 && (
        <div className="absolute top-11 right-0 left-0 z-20 max-h-85 overflow-y-auto rounded-lg border border-line bg-surface shadow-e2">
          {results.length === 0 ? (
            <p className="p-4 text-center text-xs text-fg-muted">Nothing matches that.</p>
          ) : (
            results.map((r) => (
              <button
                key={r.key}
                type="button"
                onClick={() => {
                  r.go();
                  setQuery("");
                  setOpen(false);
                }}
                className="flex w-full items-center gap-3 border-b border-line-subtle px-3.5 py-2.5 text-left transition-colors last:border-0 hover:bg-subtle"
              >
                <span className="flex size-7 shrink-0 items-center justify-center rounded-md bg-brand-subtle text-[10px] font-bold text-[var(--brand-text)]">
                  {r.initials}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-[12.5px] font-semibold text-fg">
                    {r.title}
                  </span>
                  <span className="block truncate text-[11px] text-fg-muted">{r.sub}</span>
                </span>
                <span className="text-[10px] font-bold tracking-wide text-fg-muted uppercase">
                  {r.kind}
                </span>
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}
function NotificationsMenu() {
  const [open, setOpen] = useState(false);
  const ref = useDismiss(open, () => setOpen(false));
  const navigate = useNavigate();
  const { data } = useQuery({
    queryKey: ["notifications"],
    queryFn: notificationsApi.list,
    refetchInterval: 60_000,
  });
  const alerts = data ?? [];
  const urgentCount = alerts.filter((n) => n.type === "danger").length;
  const dotColor = { danger: "bg-danger", warning: "bg-warn", primary: "bg-brand" };
  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        title="Notifications"
        aria-label="Notifications"
        className="relative flex size-9 items-center justify-center rounded-md border border-white/25 bg-white/10 text-chrome-text-hover transition-colors hover:border-white/40 hover:bg-white/20 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white/60"
      >
        <Bell className="size-[17px]" aria-hidden />
        {urgentCount > 0 && (
          <span className="absolute -top-1 -right-1 flex h-[17px] min-w-[17px] items-center justify-center rounded-full bg-danger px-1 text-[9.5px] font-bold text-on-danger ring-2 ring-chrome">
            {urgentCount}
          </span>
        )}
      </button>
      {open && (
        <div className="absolute top-11 right-0 z-20 w-86 overflow-hidden rounded-2xl border border-line bg-surface shadow-e2">
          <div className="flex items-center justify-between border-b border-line-subtle px-4 py-3">
            <span className="text-xs font-bold text-fg">Alerts</span>
            <button
              type="button"
              onClick={() => {
                setOpen(false);
                navigate("/notifications");
              }}
              className="text-[11px] font-bold text-brand hover:underline"
            >
              View all
            </button>
          </div>
          {alerts.length === 0 ? (
            <p className="p-4 text-center text-xs text-fg-muted">You're all caught up.</p>
          ) : (
            alerts.slice(0, 4).map((n) => (
              /* Same rule as the Alerts page: an alert that names something
                 opens it, and one that names nothing stays inert. */
              <NavLink
                key={n.id}
                to={n.link ?? "/notifications"}
                onClick={() => setOpen(false)}
                className="flex gap-2.5 border-b border-line-subtle px-4 py-3 transition-colors last:border-0 hover:bg-subtle"
              >
                <span className={cn("mt-1.5 size-1.5 shrink-0 rounded-full", dotColor[n.type])} />
                <span className="min-w-0">
                  <span className="block text-[12.5px] leading-snug font-semibold text-fg">
                    {n.title}
                  </span>
                  <span className="mt-0.5 block text-[11.5px] text-fg-muted">{n.description}</span>
                </span>
              </NavLink>
            ))
          )}
        </div>
      )}
    </div>
  );
}
function UserMenu() {
  const { user, isAdmin, logout } = useAuth();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const ref = useDismiss(open, () => setOpen(false));
  if (!user) return null;
  async function handleLogout() {
    await logout();
    navigate("/login", { replace: true });
  }
  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-2.5 rounded-md py-1 pr-2 pl-1 text-chrome-text-hover transition-colors hover:bg-white/[0.07]"
      >
        <span className="flex size-[30px] items-center justify-center rounded-[10px] bg-gradient-to-br from-brand to-accent text-[11px] font-bold text-on-brand">
          {initialsOf(user.full_name)}
        </span>
        <span className="hidden text-left leading-tight sm:block">
          <span className="block text-xs font-semibold text-white">{user.full_name}</span>
          <span className="block text-[9.5px] font-semibold tracking-widest text-chrome-text uppercase">
            {isAdmin ? "Administrator" : "HR"}
          </span>
        </span>
      </button>
      {open && (
        <div className="absolute top-12 right-0 z-20 w-56 rounded-2xl border border-line bg-surface p-1.5 shadow-e2">
          <p className="px-2.5 pt-1.5 pb-2 text-[9.5px] font-bold tracking-widest text-fg-muted uppercase">
            {user.email}
          </p>
          <NavLink
            to="/change-password"
            onClick={() => setOpen(false)}
            className="block rounded-md px-2.5 py-2 text-[12.5px] font-semibold text-fg-secondary transition-colors hover:bg-subtle"
          >
            Change password
          </NavLink>
          <div className="my-1 h-px bg-line-subtle" />
          <button
            type="button"
            onClick={handleLogout}
            className="block w-full rounded-md px-2.5 py-2 text-left text-[12.5px] font-semibold text-danger transition-colors hover:bg-danger-subtle"
          >
            Sign out
          </button>
        </div>
      )}
    </div>
  );
}
export default function AppShell() {
  const { isAdmin } = useAuth();
  const { theme, toggle } = useTheme();
  const { pathname } = useLocation();
  const groups = GROUPS.filter((g) => !g.adminOnly || isAdmin);
  const activeGroup =
    groups.find((g) => g.items.some((i) => isRouteActive(pathname, i.to))) ?? GROUPS[0];
  const counts = useGroupCounts(activeGroup, isAdmin);
  /* One screen in the group means there's nothing to switch between — the row
       would just restate the group tab already highlighted above it. */
  const subTabs = activeGroup.items.length > 1 ? activeGroup.items : [];
  return (
    <div className="shell-wash min-h-dvh bg-canvas">
      {/* DVein's admin chrome is the darkest step of the brand ramp — the
            company's product identity, re-graded with the theme so a dark
            console doesn't leave a lighter bar floating above it. */}
      <header className="sticky top-0 z-30 bg-gradient-to-b from-chrome to-chrome-2 shadow-[0_1px_0_rgba(0,0,0,0.2)]">
        <div className="mx-auto flex h-[62px] max-w-[1560px] items-center gap-5 px-6">
          <div className="flex shrink-0 items-center gap-2.5">
            <img src="/brand/logo-icon.png" alt="DVein Innovations" className="size-8" />
            <div className="leading-tight">
              <p className="text-[13.5px] font-extrabold tracking-widest text-white">DVEIN</p>
              <p className="text-[8.5px] font-semibold tracking-[0.24em] text-chrome-text">
                HRM CONSOLE
              </p>
            </div>
          </div>

          <SearchBox />

          <div className="ml-auto flex shrink-0 items-center gap-2">
            <NotificationsMenu />
            <button
              type="button"
              onClick={toggle}
              aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}
              className="flex size-9 items-center justify-center rounded-md border border-white/25 bg-white/10 text-chrome-text-hover transition-colors hover:border-white/40 hover:bg-white/20 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white/60"
            >
              {theme === "dark" ? (
                <Sun className="size-[17px]" />
              ) : (
                <Moon className="size-[17px]" />
              )}
            </button>
            <div className="mx-1 h-6.5 w-px bg-white/20" />
            <UserMenu />
          </div>
        </div>

        <div className="border-b border-line bg-surface">
          <nav
            aria-label="Sections"
            className="scroll-x mx-auto flex max-w-[1560px] items-center gap-1 px-6"
          >
            {groups.map((group) => (
              <GroupTab key={group.key} group={group} active={group.key === activeGroup.key} />
            ))}
          </nav>
        </div>

        {subTabs.length > 0 && (
          <div className="border-b border-line bg-subtle">
            <nav
              aria-label={activeGroup.label}
              className="scroll-x mx-auto flex max-w-[1560px] items-center gap-1.75 px-6 py-2.25"
            >
              {subTabs.map((item) => (
                <SubTab
                  key={item.to}
                  item={item}
                  active={isRouteActive(pathname, item.to)}
                  count={item.count ? counts[item.count] : undefined}
                />
              ))}
            </nav>
          </div>
        )}
      </header>

      <main className="mx-auto max-w-[1560px]">
        <Outlet />
      </main>
    </div>
  );
}
