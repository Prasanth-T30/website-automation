import { api } from "@/lib/api";
export const studentsApi = {
  list: (params) => api.get("/students", params),
  create: (data) => api.post("/students", data),
  get: (id) => api.get(`/students/${id}`),
  update: (id, data) => api.patch(`/students/${id}`, data),
  /** Admin only: move a student to a different HR. */
  reassign: (id, owner_id) => api.post(`/students/${id}/reassign`, { owner_id }),

  /** Generates the certificate, emails it, and files it under Documents. */
  issueCertificate: (id, data = {}) => api.post(`/students/${id}/certificate`, data),
  /** Preview only — downloads the PDF without emailing or filing it. */
  certificateUrl: (id) => `/api/v1/students/${id}/certificate`,
};
