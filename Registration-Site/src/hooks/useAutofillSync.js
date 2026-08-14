import { useEffect } from "react";

/**
 * Keeps react-hook-form's internal state in sync with the actual DOM value
 * of fields inside `formRef`.
 *
 * react-hook-form (in uncontrolled/register mode) normally relies on React's
 * synthetic onChange to know a field changed. Browser autofill, password
 * managers, and some form-fill tools set an input's value directly without
 * firing an event React can see, so the field looks filled on screen but
 * react-hook-form still treats it as empty — which makes "required" errors
 * appear even though the field clearly has a value.
 *
 * This hook attaches native (capture-independent) input/change listeners
 * directly on the form element and force-syncs whatever value is actually
 * in the DOM into react-hook-form via setValue, so validation always sees
 * the real value no matter how it got there.
 */
export function useAutofillSync(formRef, setValue) {
  useEffect(() => {
    const formEl = formRef.current;
    if (!formEl) return undefined;

    const syncField = (target) => {
      const name = target?.name;
      if (!name) return;
      const value = target.type === "checkbox" ? target.checked : target.value;
      setValue(name, value, { shouldValidate: true, shouldDirty: true });
    };

    const handleEvent = (e) => syncField(e.target);

    formEl.addEventListener("input", handleEvent, true);
    formEl.addEventListener("change", handleEvent, true);

    return () => {
      formEl.removeEventListener("input", handleEvent, true);
      formEl.removeEventListener("change", handleEvent, true);
    };
  }, [formRef, setValue]);
}
