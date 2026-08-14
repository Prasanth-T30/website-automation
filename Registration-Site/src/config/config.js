// This app (Registration-Site) only talks to the shared Backend API — it has
// no admin routes of its own. The Admin site is a fully separate app/URL.
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api";
export const UPLOADS_BASE_URL = API_BASE_URL.replace(/\/api\/?$/, "");
export const APP_NAME = "Internship Registration Portal";
export const COMPANY_NAME = "DVein Innovations Pvt. Ltd.";

// URL of the separate Admin site (different app, different port/domain).
export const ADMIN_SITE_URL = import.meta.env.VITE_ADMIN_SITE_URL || "http://localhost:5175";
