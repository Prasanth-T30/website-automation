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

export const saveApprovalEmail = async (id, subject, body) => {
  const { data } = await api.put(`/registrations/${id}/approval-email`, { subject, body });
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
export const exportPdfUrl = () => `${api.defaults.baseURL}/export/pdf`;

export const downloadExport = async (type) => {
  const extensionMap = {
    excel: "xlsx",
    pdf: "pdf",
  };

  try {
    const token = localStorage.getItem("admin_token");
    
    if (!token) {
      throw new Error("You are not logged in. Please log in again.");
    }

    const { data } = await api.get(`/export/${type}`, {
      responseType: "blob",
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: type === "excel" ? "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" : "application/pdf",
      },
    });

    if (data.size === 0) {
      throw new Error("No registrations to export. There is no data available.");
    }

    const url = window.URL.createObjectURL(new Blob([data]));
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", `registrations.${extensionMap[type] || "xlsx"}`);
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => window.URL.revokeObjectURL(url), 1000);
    return true;
  } catch (error) {
    // Network error handling
    if (!error.response) {
      // Network-level error
      if (error.code === "ECONNABORTED") {
        throw new Error("Request timeout. The server took too long to respond. Please try again.");
      }
      if (error.message === "Network Error") {
        throw new Error("Network error: Cannot reach the server. Check your internet connection.");
      }
      if (error.message.includes("ERR_")) {
        throw new Error("Network error: Unable to connect to the server. Check your internet connection.");
      }
    }

    // HTTP error responses
    if (error.response) {
      const status = error.response.status;
      const detail = error.response.data?.detail;

      if (status === 401) {
        throw new Error("Session expired. Please log in again.");
      }
      if (status === 403) {
        throw new Error("Access denied. You do not have permission to export data.");
      }
      if (status === 404) {
        throw new Error("Export endpoint not found. Please refresh and try again.");
      }
      if (status === 500) {
        throw new Error("Server error. Please try again later.");
      }
      if (status >= 500) {
        throw new Error(`Server error (${status}). Please try again later.`);
      }
      if (detail) {
        throw new Error(detail);
      }
    }

    // Fallback error message
    const message = error.message || `Failed to download ${type} file`;
    throw new Error(message);
  }
};

export const offerLetterUrl = (id) => `${api.defaults.baseURL}/registrations/${id}/offer-letter`;
