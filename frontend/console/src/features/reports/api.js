import { api } from "@/lib/api";
export const reportsApi = {
  list: (params) => api.get("/reports", params),
  upload: (input) => {
    const form = new FormData();
    form.append("title", input.title);
    form.append("category", input.category);
    if (input.student_id) form.append("student_id", input.student_id);
    form.append("file", input.file);
    return api.upload("/reports", form);
  },
  downloadUrl: (id) => api.url(`/reports/${id}/download`),
  remove: (id) => api.del(`/reports/${id}`),
};
