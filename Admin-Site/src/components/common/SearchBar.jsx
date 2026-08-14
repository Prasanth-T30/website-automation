import { FiSearch } from "react-icons/fi";

const SearchBar = ({ value, onChange, placeholder = "Search..." }) => (
  <div className="relative w-full max-w-sm">
    <FiSearch className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[#8494A9]" />
    <input
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      className="input-base pl-9"
    />
  </div>
);

export default SearchBar;
