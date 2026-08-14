/**
 * Typed fetch wrapper for the Dvein HRM API.
 *
 * Auth rides on httpOnly cookies, so every request sends credentials and
 * mutations carry the double-submit CSRF token. Tokens are never read from or
 * written to JavaScript-accessible storage.
 */

const BASE = "/api/v1";
const CSRF_COOKIE = "dvein_csrf";
const CSRF_HEADER = "X-CSRF-Token";

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly detail: string,
    readonly body?: unknown,
  ) {
    super(detail);
    this.name = "ApiError";
  }

  get isAuthError(): boolean {
    return this.status === 401 || this.status === 403;
  }
}

function readCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match?.[1] ? decodeURIComponent(match[1]) : null;
}

type Query = Record<string, string | number | boolean | null | undefined>;

/** Build a query string, dropping empty values so filters stay clean. */
export function qs(params?: Query): string {
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
let refreshInFlight: Promise<boolean> | null = null;

async function refreshSession(): Promise<boolean> {
  // No CSRF cookie means there was never a session to refresh. Skipping here
  // keeps anonymous page loads to a single request instead of two.
  const csrf = readCookie(CSRF_COOKIE);
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

async function send(path: string, init: RequestInit): Promise<Response> {
  const method = (init.method ?? "GET").toUpperCase();
  const headers = new Headers(init.headers);

  if (init.body !== undefined && !(init.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  if (method !== "GET" && method !== "HEAD") {
    const token = readCookie(CSRF_COOKIE);
    if (token) headers.set(CSRF_HEADER, token);
  }

  return fetch(`${BASE}${path}`, { ...init, headers, credentials: "include" });
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  let res: Response;
  try {
    res = await send(path, init);

    if (res.status === 401 && !NO_REFRESH.has(path) && (await refreshSession())) {
      res = await send(path, init);
    }
  } catch {
    throw new ApiError(0, "Cannot reach the server. Check your connection.");
  }

  if (res.status === 204) return undefined as T;

  const isJson = res.headers.get("content-type")?.includes("application/json");
  const payload = isJson ? await res.json().catch(() => null) : null;

  if (!res.ok) {
    const detail =
      (payload as { detail?: string } | null)?.detail ?? `Request failed (${res.status})`;
    throw new ApiError(res.status, detail, payload);
  }

  return payload as T;
}

export const api = {
  get: <T>(path: string, params?: Query) => request<T>(`${path}${qs(params)}`),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) }),
  patch: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "PATCH", body: JSON.stringify(body) }),
  del: <T>(path: string) => request<T>(path, { method: "DELETE" }),
  upload: <T>(path: string, form: FormData) =>
    request<T>(path, { method: "POST", body: form }),
  /** Absolute URL for links the browser fetches directly (downloads, PDFs). */
  url: (path: string, params?: Query) => `${BASE}${path}${qs(params)}`,
};
