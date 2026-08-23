import { api } from "@/lib/api";
export const batchesApi = {
  list: (params) => api.get("/batches", params),
  get: (id) => api.get(`/batches/${id}`),
  create: (data) => api.post("/batches", data),
  update: (id, data) => api.patch(`/batches/${id}`, data),
  delete: (id) => api.del(`/batches/${id}`),

  /** Everyone on the batch. Fee fields come back null for other HRs' students. */
  roster: (id) => api.get(`/batches/${id}/roster`),
  /** Money for the students the caller may see — theirs, or all for an admin. */
  finance: (id) => api.get(`/batches/${id}/finance`),
};
