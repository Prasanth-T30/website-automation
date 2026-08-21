import { api } from "@/lib/api";

export const announcementsApi = {
  /** Everyone reads these; only an admin can write one. */
  list: (params) => api.get("/announcements", params),
  create: (data) => api.post("/announcements", data),
  remove: (id) => api.del(`/announcements/${id}`),
};
