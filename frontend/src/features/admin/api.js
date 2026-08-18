import { api } from "@/lib/api";
export const adminApi = {
  hrPerformance: () => api.get("/admin/hr-performance"),
};
