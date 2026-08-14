import { createContext, useEffect, useState } from "react";

import { getStoredAdmin, login as loginRequest, logout as logoutRequest } from "../services/authService";

export const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [admin, setAdmin] = useState(getStoredAdmin());
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const stored = getStoredAdmin();
    if (stored) setAdmin(stored);
  }, []);

  const login = async (email, password) => {
    setLoading(true);
    try {
      const result = await loginRequest(email, password);
      localStorage.setItem("admin_token", result.access_token);
      localStorage.setItem("admin_user", JSON.stringify(result.admin));
      setAdmin(result.admin);
      return result;
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    logoutRequest();
    setAdmin(null);
  };

  return (
    <AuthContext.Provider value={{ admin, loading, login, logout, isAuthenticated: !!admin }}>
      {children}
    </AuthContext.Provider>
  );
};
