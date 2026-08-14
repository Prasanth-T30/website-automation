import api from "./api";

export const login = async (email, password) => {
  const { data } = await api.post("/auth/login", { email, password });
  return data.data; // { access_token, token_type, admin }
};

export const logout = () => {
  localStorage.removeItem("admin_token");
  localStorage.removeItem("admin_user");
};

export const getStoredAdmin = () => {
  const raw = localStorage.getItem("admin_user");
  return raw ? JSON.parse(raw) : null;
};
