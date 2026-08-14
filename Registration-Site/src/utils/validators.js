export const isValidEmail = (value) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);

export const isValidPhone = (value) => /^[0-9]{10,15}$/.test((value || "").replace(/\D/g, ""));

export const isValidImageFile = (file) => {
  if (!file) return false;
  const allowed = ["image/jpeg", "image/jpg", "image/png"];
  return allowed.includes(file.type);
};

export const isFileSizeValid = (file, maxMB = 5) => {
  if (!file) return false;
  return file.size <= maxMB * 1024 * 1024;
};

export const required = (value) => (value !== undefined && value !== null && `${value}`.trim() !== "") || "This field is required";
