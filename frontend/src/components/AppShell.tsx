import {
  Award,
  Banknote,
  Bell,
  CalendarCheck,
  ChevronLeft,
  FileText,
  GraduationCap,
  KanbanSquare,
  LayoutDashboard,
  Layers,
  LogOut,
  Moon,
  PanelLeft,
  Settings,
  Sun,
  UserCog,
} from "lucide-react";
import { useState, type ComponentType } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";

import { Avatar } from "@/components/ui/Avatar";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { useAuth } from "@/features/auth/AuthProvider";
import { cn } from "@/lib/cn";
import { useTheme } from "@/lib/theme";

interface NavItem {
  to: string;
  label: string;
  icon: ComponentType<{ className?: string }>;
  /** Admin manages the HR team and institute config — HRs never need these. */
  adminOnly?: boolean;
  /** Screens whose backend hasn't landed yet render mock data — flagged here
   * only so the badge next to the label stays accurate; the route itself is
   * always reachable. */
  preview?: boolean;
}

const NAV: NavItem[] = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/pipeline", label: "Pipeline", icon: KanbanSquare, preview: true },
  { to: "/applications", label: "Applications", icon: FileText, preview: true },
  { to: "/students", label: "Students", icon: GraduationCap, preview: true },
  { to: "/batches", label: "Batches", icon: Layers, preview: true },
  { to: "/attendance", label: "Attendance", icon: CalendarCheck, preview: true },
  { to: "/payments", label: "Payments", icon: Banknote, preview: true },
  { to: "/reports", label: "Certificates", icon: Award, preview: true },
  { to: "/notifications", label: "Notifications", icon: Bell, preview: true },
  { to: "/admin/users", label: "Users", icon: UserCog, adminOnly: true },
  { to: "/settings", label: "Settings", icon: Settings, adminOnly: true, preview: true },
];

function NavRow({ item, collapsed }: { item: NavItem; collapsed: boolean }) {
  const Icon = item.icon;
  const shared =
    "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors";

  return (
    <NavLink
      to={item.to}
      end={item.to === "/"}
      className={({ isActive }) =>
        cn(
          shared,
          isActive
            ? "bg-white/10 text-white"
            : "text-chrome-text hover:bg-white/5 hover:text-chrome-text-hover",
        )
      }
      title={collapsed ? item.label : undefined}
    >
      <Icon className="size-[18px] shrink-0" aria-hidden />
      {!collapsed && (
        <>
          <span className="truncate">{item.label}</span>
          {item.preview && (
            <span
              className="ml-auto size-1.5 shrink-0 rounded-full bg-accent-400"
              title="Preview data — not yet wired to the backend"
            />
          )}
        </>
      )}
    </NavLink>
  );
}

export default function AppShell() {
  const { user, isAdmin, logout } = useAuth();
  const { theme, toggle } = useTheme();
  const navigate = useNavigate();
  const [collapsed, setCollapsed] = useState(false);

  // Admin manages the HR team and institute config; every other module is
  // shared, with each screen narrowing its own data to "mine" for HR (e.g.
  // Dashboard's stats, the HR-performance table) rather than hiding outright.
  const items = NAV.filter((i) => !i.adminOnly || isAdmin);

  async function handleLogout() {
    await logout();
    navigate("/login", { replace: true });
  }

  return (
    <div className="flex min-h-dvh bg-canvas">
      {/* Dvein's admin chrome is fixed dark-navy — the company's real product
          identity, independent of the content area's light/dark toggle. */}
      <aside
        className={cn(
          "sticky top-0 flex h-dvh flex-col border-r border-chrome-border bg-chrome transition-[width] duration-200",
          collapsed ? "w-16" : "w-60",
        )}
      >
        <div className="flex h-16 items-center gap-2.5 border-b border-chrome-border px-4">
          <img src="/brand/logo-icon.png" alt="" className="size-8 shrink-0" />
          {!collapsed && (
            <div className="min-w-0 leading-tight">
              <p className="truncate text-sm font-extrabold tracking-tight text-white">Dvein</p>
              <p className="truncate text-[10px] font-semibold tracking-wide text-chrome-text uppercase">
                HRM Console
              </p>
            </div>
          )}
        </div>

        <nav className="flex flex-1 flex-col gap-1 overflow-y-auto p-3" aria-label="Main">
          {items.map((item) => (
            <NavRow key={item.to} item={item} collapsed={collapsed} />
          ))}
        </nav>

        <button
          type="button"
          onClick={() => setCollapsed((c) => !c)}
          className="flex items-center gap-3 border-t border-chrome-border px-4 py-3 text-sm text-chrome-text transition-colors hover:bg-white/5 hover:text-chrome-text-hover"
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? (
            <PanelLeft className="size-[18px]" aria-hidden />
          ) : (
            <>
              <ChevronLeft className="size-[18px]" aria-hidden />
              <span>Collapse</span>
            </>
          )}
        </button>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-10 flex h-16 items-center gap-3 border-b border-line-subtle bg-surface px-6">
          <div className="ml-auto flex items-center gap-3">
            <button
              type="button"
              onClick={toggle}
              aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}
              className="flex size-9 items-center justify-center rounded-md text-fg-secondary transition-colors hover:bg-subtle"
            >
              {theme === "dark" ? <Sun className="size-[18px]" /> : <Moon className="size-[18px]" />}
            </button>

            {user && (
              <div className="flex items-center gap-2.5 border-l border-line-subtle pl-3">
                <Avatar name={user.full_name} />
                <div className="hidden leading-tight sm:block">
                  <p className="text-xs font-semibold text-fg">{user.full_name}</p>
                  <Badge tone={isAdmin ? "brand" : "neutral"} className="mt-0.5">
                    {isAdmin ? "Administrator" : "HR"}
                  </Badge>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={handleLogout}
                  aria-label="Sign out"
                  title="Sign out"
                >
                  <LogOut className="size-[18px]" />
                </Button>
              </div>
            )}
          </div>
        </header>

        <main className="min-w-0 flex-1 shell-wash">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
