// This app (Admin-Site) only serves the admin login + dashboard — it has no
// public registration routes of its own. That's a fully separate app/URL.
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api";
export const UPLOADS_BASE_URL = API_BASE_URL.replace(/\/api\/?$/, "");
export const APP_NAME = "DVein Admin Panel";
export const COMPANY_NAME = "DVein Innovations Pvt. Ltd.";

// URL of the separate public Registration site (different app, different port/domain).
export const REGISTRATION_SITE_URL = import.meta.env.VITE_REGISTRATION_SITE_URL || "http://localhost:5174";
