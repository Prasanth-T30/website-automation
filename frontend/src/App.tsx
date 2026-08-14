import { Route, Routes } from "react-router-dom";

import AppShell from "@/components/AppShell";
import { RequireAdmin, RequireAuth } from "@/features/auth/RequireAuth";
import Applications from "@/routes/Applications";
import Attendance from "@/routes/Attendance";
import Batches from "@/routes/Batches";
import ChangePassword from "@/routes/ChangePassword";
import Dashboard from "@/routes/Dashboard";
import Login from "@/routes/Login";
import NotFound from "@/routes/NotFound";
import Notifications from "@/routes/Notifications";
import Payments from "@/routes/Payments";
import Pipeline from "@/routes/Pipeline";
import Reports from "@/routes/Reports";
import Settings from "@/routes/Settings";
import Students from "@/routes/Students";
import Users from "@/routes/admin/Users";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />

      {/* Outside the shell: a forced password change must not expose the app. */}
      <Route
        path="/change-password"
        element={
          <RequireAuth>
            <ChangePassword />
          </RequireAuth>
        }
      />

      <Route
        element={
          <RequireAuth>
            <AppShell />
          </RequireAuth>
        }
      >
        <Route index element={<Dashboard />} />
        <Route path="/pipeline" element={<Pipeline />} />
        <Route path="/applications" element={<Applications />} />
        <Route path="/students" element={<Students />} />
        <Route path="/batches" element={<Batches />} />
        <Route path="/attendance" element={<Attendance />} />
        <Route path="/payments" element={<Payments />} />
        <Route path="/reports" element={<Reports />} />
        <Route path="/notifications" element={<Notifications />} />
        <Route
          path="/admin/users"
          element={
            <RequireAdmin>
              <Users />
            </RequireAdmin>
          }
        />
        <Route
          path="/settings"
          element={
            <RequireAdmin>
              <Settings />
            </RequireAdmin>
          }
        />
      </Route>

      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}
