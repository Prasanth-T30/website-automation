import { api } from "@/lib/api";
export const usersApi = {
  list: () => api.get("/admin/users"),
  create: (data) => api.post("/admin/users", data),
  update: (id, data) => api.patch(`/admin/users/${id}`, data),
  resetPassword: (id) => api.post(`/admin/users/${id}/reset-password`),
  delete: (id) => api.del(`/admin/users/${id}`),
};
