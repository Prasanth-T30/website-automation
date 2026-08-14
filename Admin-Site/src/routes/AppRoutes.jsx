import { Navigate, Route, Routes } from "react-router-dom";

import AdminLogin from "../pages/auth/AdminLogin";
import NotFound from "../pages/error/NotFound";
import Dashboard from "../pages/dashboard/Dashboard";
import Registrations from "../pages/dashboard/Registrations";
import RegistrationDetails from "../pages/dashboard/RegistrationDetails";
import Analytics from "../pages/dashboard/Analytics";
import Settings from "../pages/dashboard/Settings";
import Profile from "../pages/profile/Profile";
import ProtectedRoute from "./ProtectedRoute";

// This app only ever serves the Admin experience: login, then dashboard.
// The public registration flow lives in a completely separate app/URL (see Registration-Site).
const AppRoutes = () => (
  <Routes>
    <Route path="/" element={<Navigate to="/login" replace />} />
    <Route path="/login" element={<AdminLogin />} />

    <Route element={<ProtectedRoute />}>
      <Route path="/dashboard" element={<Dashboard />} />
      <Route path="/registrations" element={<Registrations />} />
      <Route path="/registrations/:id" element={<RegistrationDetails />} />
      <Route path="/analytics" element={<Analytics />} />
      <Route path="/settings" element={<Settings />} />
      <Route path="/profile" element={<Profile />} />
    </Route>

    <Route path="*" element={<NotFound />} />
  </Routes>
);

export default AppRoutes;
