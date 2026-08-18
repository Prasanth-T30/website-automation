import { api } from "@/lib/api";
export const authApi = {
  login: (email, password) => api.post("/auth/login", { email, password }),
  logout: () => api.post("/auth/logout"),
  me: () => api.get("/auth/me"),
  changePassword: (currentPassword, newPassword) =>
    api.post("/auth/change-password", {
      current_password: currentPassword,
      new_password: newPassword,
    }),
};
