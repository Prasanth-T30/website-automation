/**
 * Typed fetch wrapper for the Dvein HRM API.
 *
 * Auth rides on httpOnly cookies, so every request sends credentials and
 * mutations carry the double-submit CSRF token. Tokens are never read from or
 * written to JavaScript-accessible storage.
 */
/**
 * Where the API lives.
 *
 * Empty (the default) means same-origin: a dev proxy or a hosting rewrite
 * puts the API under /api on this very host, which keeps session cookies
 * same-site and is the simplest thing that works.
 *
 * Set VITE_API_URL when the API is deployed somewhere else entirely. The
 * backend must then allow this origin in CORS_ORIGINS and set
 * COOKIE_SAMESITE=none, or the browser will drop the session cookie without
 * telling anyone.
 */
const API_ROOT = (import.meta.env.VITE_API_URL ?? "").replace(/\/+$/, "");
const BASE = `${API_ROOT}/api/v1`;
const CSRF_COOKIE = "dvein_csrf";
const CSRF_HEADER = "X-CSRF-Token";
export class ApiError extends Error {
  status;
  detail;
  body;
  constructor(status, detail, body) {
    super(detail);
    this.status = status;
    this.detail = detail;
    this.body = body;
    this.name = "ApiError";
  }
  get isAuthError() {
    return this.status === 401 || this.status === 403;
  }
}
/**
 * The CSRF token, held in memory.
 *
 * The server also sets it as a readable cookie, which is enough when the
 * console and the API share an origin. They may not: a cross-origin console
 * cannot read the API's cookies at all, so the token also comes back in the
 * login response and is kept here. Memory rather than localStorage, so it
 * dies with the tab and is never readable by an injected script later.
 */
let csrfToken = null;

/** Called by the auth layer whenever a response carries a fresh token. */
export function rememberCsrfToken(token) {
  if (token) csrfToken = token;
}

export function forgetCsrfToken() {
  csrfToken = null;
}

/** In-memory token first, cookie second — the cookie is unreadable when the
 *  API is on another origin, and absent on a first load after a reload. */
function currentCsrf() {
  return csrfToken ?? readCookie(CSRF_COOKIE);
}

function readCookie(name) {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match?.[1] ? decodeURIComponent(match[1]) : null;
}
/** Build a query string, dropping empty values so filters stay clean. */
export function qs(params) {
  if (!params) return "";
  const sp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== "") sp.append(k, String(v));
  }
  const s = sp.toString();
  return s ? `?${s}` : "";
}
/** Endpoints that must never trigger the refresh-and-retry cycle. */
const NO_REFRESH = new Set(["/auth/login", "/auth/refresh", "/auth/logout"]);
/**
 * In-flight refresh, shared across callers.
 *
 * Access tokens last 15 minutes, so several parallel queries commonly 401 at
 * once. Without this, each would fire its own refresh and the losers would
 * retry with tokens that had already been rotated away.
 */
let refreshInFlight = null;
async function refreshSession() {
  // No CSRF cookie means there was never a session to refresh. Skipping here
  // keeps anonymous page loads to a single request instead of two.
  const csrf = currentCsrf();
  if (!csrf) return false;
  refreshInFlight ??= (async () => {
    try {
      const headers = new Headers({ [CSRF_HEADER]: csrf });
      const res = await fetch(`${BASE}/auth/refresh`, {
        method: "POST",
        headers,
        credentials: "include",
      });
      return res.ok;
    } catch {
      return false;
    } finally {
      // Cleared on the next tick so concurrent callers all observe this result.
      setTimeout(() => {
        refreshInFlight = null;
      }, 0);
    }
  })();
  return refreshInFlight;
}
async function send(path, init) {
  const method = (init.method ?? "GET").toUpperCase();
  const headers = new Headers(init.headers);
  if (init.body !== undefined && !(init.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  if (method !== "GET" && method !== "HEAD") {
    const token = currentCsrf();
    if (token) headers.set(CSRF_HEADER, token);
  }
  return fetch(`${BASE}${path}`, { ...init, headers, credentials: "include" });
}
/** One request, retried once through a token refresh if the session lapsed. */
async function sendWithRefresh(path, init) {
  try {
    const res = await send(path, init);
    if (res.status === 401 && !NO_REFRESH.has(path) && (await refreshSession())) {
      return await send(path, init);
    }
    return res;
  } catch {
    throw new ApiError(0, "Cannot reach the server. Check your connection.");
  }
}
async function request(path, init = {}) {
  const res = await sendWithRefresh(path, init);
  if (res.status === 204) return undefined;
  const isJson = res.headers.get("content-type")?.includes("application/json");
  const payload = isJson ? await res.json().catch(() => null) : null;
  if (!res.ok) {
    const detail = payload?.detail ?? `Request failed (${res.status})`;
    throw new ApiError(res.status, detail, payload);
  }
  return payload;
}
export const api = {
  get: (path, params) => request(`${path}${qs(params)}`),
  post: (path, body) =>
    request(path, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) }),
  patch: (path, body) => request(path, { method: "PATCH", body: JSON.stringify(body) }),
  put: (path, body) => request(path, { method: "PUT", body: JSON.stringify(body) }),
  del: (path) => request(path, { method: "DELETE" }),
  upload: (path, form) => request(path, { method: "POST", body: form }),
  /**
   * POST that comes back as a file rather than JSON.
   *
   * For documents the server renders from data too personal to put in a URL:
   * a GET would leave the student's name and college in every access log
   * between here and the API.
   */
  postBlob: async (path, body) => {
    const res = await sendWithRefresh(path, {
      method: "POST",
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    if (!res.ok) {
      const payload = res.headers.get("content-type")?.includes("application/json")
        ? await res.json().catch(() => null)
        : null;
      throw new ApiError(res.status, payload?.detail ?? `Request failed (${res.status})`, payload);
    }
    return res.blob();
  },
  /** Absolute URL for links the browser fetches directly (downloads, PDFs). */
  url: (path, params) => `${BASE}${path}${qs(params)}`,
};
