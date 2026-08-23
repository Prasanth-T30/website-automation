const VARIANTS = {
  primary: "btn-primary",
  secondary: "btn-secondary",
  danger: "btn-danger",
  success: "btn-success",
};

const Button = ({ children, variant = "primary", loading = false, className = "", disabled, ...rest }) => (
  <button
    className={`${VARIANTS[variant] || VARIANTS.primary} ${className}`}
    disabled={disabled || loading}
    {...rest}
  >
    {loading && (
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white" />
    )}
    {children}
  </button>
);

export default Button;
