import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "@/app/auth-context";
import type { UserRole } from "@/types/api";

export function ProtectedRoute(): JSX.Element {
  const { isAuthenticated } = useAuth();
  const location = useLocation();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  return <Outlet />;
}

export function RoleRoute({ allowedRoles }: { allowedRoles: UserRole[] }): JSX.Element {
  const { user } = useAuth();

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  const hasAccess = user.roles.some((role) => allowedRoles.includes(role));
  if (!hasAccess) {
    return <Navigate to="/chat" replace />;
  }

  return <Outlet />;
}
