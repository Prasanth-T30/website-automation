import api from "./api";

export const submitRegistration = async (formData) => {
  const { data } = await api.post("/register", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data.data;
};

export const getRegistrations = async (params) => {
  const { data } = await api.get("/registrations", { params });
  return data; // { data, total, page, page_size, total_pages }
};

export const getRegistration = async (id) => {
  const { data } = await api.get(`/registrations/${id}`);
  return data.data;
};

export const approveRegistration = async (id, subject, body) => {
  const { data } = await api.put(`/registrations/${id}/approve`, { subject, body });
  return data.data;
};

export const rejectRegistration = async (id, reason) => {
  const { data } = await api.put(`/registrations/${id}/reject`, { reason });
  return data.data;
};

export const deleteRegistration = async (id) => {
  const { data } = await api.delete(`/registrations/${id}`);
  return data;
};

export const getDashboardSummary = async () => {
  const { data } = await api.get("/dashboard");
  return data.data;
};

export const getAnalytics = async () => {
  const { data } = await api.get("/dashboard/analytics");
  return data.data;
};

export const exportExcelUrl = () => `${api.defaults.baseURL}/export/excel`;
export const exportCsvUrl = () => `${api.defaults.baseURL}/export/csv`;

export const downloadExport = async (type) => {
  const { data } = await api.get(`/export/${type}`, { responseType: "blob" });
  const url = window.URL.createObjectURL(new Blob([data]));
  const link = document.createElement("a");
  link.href = url;
  link.setAttribute("download", `registrations.${type === "excel" ? "xlsx" : "csv"}`);
  document.body.appendChild(link);
  link.click();
  link.remove();
};

export const offerLetterUrl = (id) => `${api.defaults.baseURL}/registrations/${id}/offer-letter`;
