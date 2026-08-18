import { api } from "@/lib/api";
export const batchesApi = {
  list: (params) => api.get("/batches", params),
  get: (id) => api.get(`/batches/${id}`),
  create: (data) => api.post("/batches", data),
  update: (id, data) => api.patch(`/batches/${id}`, data),
  delete: (id) => api.del(`/batches/${id}`),
};
