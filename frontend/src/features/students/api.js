import { api } from "@/lib/api";
export const studentsApi = {
  list: (params) => api.get("/students", params),
  create: (data) => api.post("/students", data),
  get: (id) => api.get(`/students/${id}`),
  update: (id, data) => api.patch(`/students/${id}`, data),

  /** Generates the certificate, emails it, and files it under Documents. */
  issueCertificate: (id, data = {}) => api.post(`/students/${id}/certificate`, data),
  /** Preview only — downloads the PDF without emailing or filing it. */
  certificateUrl: (id) => `/api/v1/students/${id}/certificate`,
};
