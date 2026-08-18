import { api } from "@/lib/api";
export const settingsApi = {
  get: () => api.get("/settings"),
  update: (data) => api.put("/settings", data),
};
