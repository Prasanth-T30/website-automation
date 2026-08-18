// This app is the public registration form. It writes to exactly one endpoint
// on the HRM backend (`POST /public/applications`) and reads one (`/public/
// choices`) — there is no admin surface here, and no separate database. A
// submission lands straight in the HRM's claim queue for an HR to pick up.
//
// Relative by default so the browser stays same-origin with the API in dev
// (Vite proxies /api) and in production (one domain behind the reverse proxy).
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api/v1";
export const APP_NAME = "Internship Registration Portal";
export const COMPANY_NAME = "DVein Innovations Pvt. Ltd.";
