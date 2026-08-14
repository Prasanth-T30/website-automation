const Input = ({ label, error, className = "", required, as = "input", children, ...rest }) => {
  const Component = as;
  return (
    <div className={className}>
      {label && (
        <label className="mb-1.5 block text-xs font-semibold text-[#41536B]">
          {label} {required && <span className="text-[#DC5B5B]">*</span>}
        </label>
      )}
      {as === "select" ? (
        <select className="input-base" {...rest}>
          {children}
        </select>
      ) : as === "textarea" ? (
        <textarea className="input-base" {...rest} />
      ) : (
        <Component className="input-base" {...rest} />
      )}
      {error && <p className="mt-1 text-xs font-medium text-[#C2453F]">{error}</p>}
    </div>
  );
};

export default Input;
