import { Link } from "react-router-dom";

import { APP_NAME } from "../../config/config";

const Navbar = () => (
  <header className="sticky top-0 z-40 border-b border-[#1C2A3E] bg-[#0E1A2B]">
    <div className="mx-auto flex h-[46px] max-w-6xl items-center justify-center px-4">
      <Link to="/" className="flex items-center gap-2.5">
        <img src="/brand/logo-icon.png" alt={APP_NAME} className="h-5 w-auto" />
        <span className="text-xs font-bold uppercase tracking-[.12em] text-[#94A3B8]">Registration Portal</span>
      </Link>
    </div>
  </header>
);

export default Navbar;
