import { NavLink } from "react-router-dom";
import { FiFileText, FiGrid, FiList, FiSettings, FiUser } from "react-icons/fi";

const links = [
  { to: "/dashboard", label: "Dashboard", icon: FiGrid },
  { to: "/registrations", label: "Registrations", icon: FiList },
  { to: "/analytics", label: "Analytics", icon: FiFileText },
  { to: "/settings", label: "Settings", icon: FiSettings },
  { to: "/profile", label: "Profile", icon: FiUser },
];

const Sidebar = () => (
  <aside className="sticky top-0 hidden h-screen w-60 shrink-0 flex-col border-r border-[#1C2A3E] bg-[#0E1A2B] px-3 py-5 md:flex">
    <div className="mb-7 flex items-center gap-2 px-2">
      <img src="/brand/logo-icon.png" alt="DVein Innovations" className="h-8 w-auto" />
      <div>
        <p className="text-sm font-extrabold text-white">DVein Admin</p>
        <p className="text-xs font-semibold text-[#8FA1B8]">Internship Portal</p>
      </div>
    </div>
    <nav className="flex flex-1 flex-col gap-1">
      {links.map(({ to, label, icon: Icon }) => (
        <NavLink
          key={to}
          to={to}
          className={({ isActive }) =>
            `flex items-center gap-3 rounded-[11px] px-3 py-2.5 text-sm font-bold transition-colors ${
              isActive ? "bg-[#EAF2FB] text-[#2A5488]" : "text-[#9AABC0] hover:bg-white/5 hover:text-white"
            }`
          }
        >
          <Icon size={17} />
          {label}
        </NavLink>
      ))}
    </nav>
  </aside>
);

export default Sidebar;
