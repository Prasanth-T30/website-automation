import { api } from "@/lib/api";
export const attendanceApi = {
  list: (params) => api.get("/attendance", params),
  mark: (data) => api.post("/attendance", data),
};
