import { COMPANY_NAME, COPYRIGHT_YEAR } from "../../config/config";

const Footer = () => (
  <footer className="mt-auto border-t border-[#DEE7F1] bg-white/70 py-5 text-center text-xs font-medium text-[#7C8DA3]">
    &copy; {COPYRIGHT_YEAR} {COMPANY_NAME} - All rights reserved.
  </footer>
);

export default Footer;
