const Loader = ({ label = "Loading..." }) => (
  <div className="flex flex-col items-center justify-center gap-3 py-16 text-gray-500">
    <span className="h-10 w-10 animate-spin rounded-full border-4 border-primary-100 border-t-primary-500" />
    <p className="text-sm">{label}</p>
  </div>
);

export default Loader;
