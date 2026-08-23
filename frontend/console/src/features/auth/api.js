import { api, forgetCsrfToken, rememberCsrfToken } from "@/lib/api";

/**
 * Every endpoint that issues or rotates a session hands back a CSRF token,
 * and each one is captured here.
 *
 * When the console and the API share an origin the readable cookie would be
 * enough. They need not be: deployed separately, JavaScript cannot see the
 * API's cookies at all. Keeping the token in memory covers both cases.
 *
 * The capture has to happen on password-change as well, not just login —
 * that endpoint rotates the token, so a client still holding the previous
 * one would fail its very next write with a CSRF error that looks like
 * nothing in particular.
 */
export const authApi = {
  login: async (email, password) => {
    const session = await api.post("/auth/login", { email, password });
    rememberCsrfToken(session?.csrf_token);
    return session;
  },

  logout: async () => {
    try {
      return await api.post("/auth/logout");
    } finally {
      // Cleared even if the request failed: the local session is over either
      // way, and a stale token must not outlive it.
      forgetCsrfToken();
    }
  },

  me: () => api.get("/auth/me"),

  changePassword: async (currentPassword, newPassword) => {
    const session = await api.post("/auth/change-password", {
      current_password: currentPassword,
      new_password: newPassword,
    });
    rememberCsrfToken(session?.csrf_token);
    return session;
  },
};
