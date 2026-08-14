import { Link } from "react-router-dom";

import { APP_NAME } from "../../config/config";

const Navbar = () => (
  <header className="sticky top-0 z-40 border-b border-[#1C2A3E] bg-[#0E1A2B]">
    <div className="mx-auto flex h-[46px] max-w-6xl items-center justify-between px-4">
      <Link to="/" className="flex items-center gap-2.5">
        <img src="/brand/logo-icon.png" alt={APP_NAME} className="h-5 w-auto" />
        <span className="text-xs font-bold uppercase tracking-[.12em] text-[#94A3B8]">Internship Portal</span>
      </Link>
      <span className="hidden rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs font-semibold text-[#C8D5E4] sm:inline-flex">
        Student registration
      </span>
    </div>
  </header>
);

export default Navbar;
