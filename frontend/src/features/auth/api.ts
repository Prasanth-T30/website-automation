import { api } from "@/lib/api";

import type { SessionResponse, User } from "./types";

export const authApi = {
  login: (email: string, password: string) =>
    api.post<SessionResponse>("/auth/login", { email, password }),

  logout: () => api.post<void>("/auth/logout"),

  me: () => api.get<User>("/auth/me"),

  changePassword: (currentPassword: string, newPassword: string) =>
    api.post<void>("/auth/change-password", {
      current_password: currentPassword,
      new_password: newPassword,
    }),
};
