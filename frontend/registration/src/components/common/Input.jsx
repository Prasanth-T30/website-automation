import { forwardRef } from "react";

/**
 * Label + control + error message, as one field.
 *
 * Must forward its ref: every caller spreads `{...register("field")}` from
 * react-hook-form, and that object carries a `ref`. A plain function component
 * silently swallows it, which costs the form its focus-on-error behaviour —
 * submitting a long form with an invalid field below the fold would appear to
 * do nothing at all.
 *
 * The three controls stay on separate branches rather than one dynamic tag:
 * `<input>` is a void element, so handing it a `children` prop — even
 * `undefined` — makes React complain.
 */
const Input = forwardRef(
  ({ label, error, className = "", required, as = "input", children, ...rest }, ref) => (
    <div className={className}>
      {label && (
        <label className="dv-label">
          {label} {required && <span className="text-[#DC5B5B]">*</span>}
        </label>
      )}
      {as === "select" ? (
        <select ref={ref} className="input-base" {...rest}>
          {children}
        </select>
      ) : as === "textarea" ? (
        <textarea ref={ref} className="input-base" {...rest} />
      ) : (
        <input ref={ref} className="input-base" {...rest} />
      )}
      {error && (
        <p data-error-message className="mt-1 text-xs font-medium text-[#C2453F]">
          {error}
        </p>
      )}
    </div>
  ),
);

Input.displayName = "Input";

export default Input;
