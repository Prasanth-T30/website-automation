// This app is the public registration form. It writes to exactly one endpoint
// on the HRM backend (`POST /public/applications`) and reads one (`/public/
// choices`) — there is no admin surface here, and no separate database. A
// submission lands straight in the HRM's claim queue for an HR to pick up.
//
// Relative by default so the browser stays same-origin with the API in dev
// (Vite proxies /api) and wherever a reverse proxy puts both on one domain.
//
// Set VITE_API_URL to the API's origin when it is hosted separately — the
// same variable the console uses, so one deployment does not silently keep
// pointing at the wrong place because the two apps disagreed on a name.
// VITE_API_BASE_URL is still honoured for existing deployments that set it.
const apiOrigin = (import.meta.env.VITE_API_URL ?? "").replace(/\/+$/, "");
export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || (apiOrigin ? `${apiOrigin}/api/v1` : "/api/v1");
export const APP_NAME = "Internship Registration Portal";
export const COMPANY_NAME = "DVein Innovations Pvt. Ltd.";

// The year in the footer's copyright line.
//
// Fixed rather than `new Date().getFullYear()`: that printed whatever year the
// visitor's clock said, so the notice moved on its own and could disagree with
// the same notice elsewhere. Copyright dates from when the work was published,
// not from today, so it is stated once here and changed on purpose.
export const COPYRIGHT_YEAR = 2025;
