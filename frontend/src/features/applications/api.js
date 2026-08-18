import { api } from "@/lib/api";
export const applicationsApi = {
  list: (params) => api.get("/applications", params),
  claim: (id) => api.post(`/applications/${id}/claim`),
  approve: (id, data) => api.post(`/applications/${id}/approve`, data),
  reject: (id, reason) => api.post(`/applications/${id}/reject`, { reason }),
  offerLetterUrl: (id) => api.url(`/applications/${id}/offer-letter`),
};
