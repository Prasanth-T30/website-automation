import { api } from "@/lib/api";
export const notificationsApi = {
  list: () => api.get("/notifications"),
};
