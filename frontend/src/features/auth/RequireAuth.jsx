import { Navigate, useLocation } from "react-router-dom";
import { LoadingState } from "@/components/ui/States";
import { useAuth } from "./AuthProvider";
/** Gate for any route that needs a signed-in user. */
export function RequireAuth({ children }) {
  const { user, isLoading } = useAuth();
  const location = useLocation();
  if (isLoading) return <LoadingState label="Checking your session…" />;
  if (!user) {
    // Remember where they were headed so login can send them back.
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  // A forced password change blocks everything else until it is done.
  if (user.must_change_password && location.pathname !== "/change-password") {
    return <Navigate to="/change-password" replace />;
  }
  return <>{children}</>;
}
/** Gate for admin-only routes. */
export function RequireAdmin({ children }) {
  const { user, isLoading } = useAuth();
  if (isLoading) return <LoadingState />;
  if (!user) return <Navigate to="/login" replace />;
  if (user.role !== "admin") return <Navigate to="/" replace />;
  return <>{children}</>;
}
