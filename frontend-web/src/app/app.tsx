import { Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "@/app/app-shell";
import { ProtectedRoute, RoleRoute } from "@/app/route-guards";
import { useAuth } from "@/app/auth-context";
import { AdminDashboardPage } from "@/pages/admin-dashboard-page";
import { ChatPage } from "@/pages/chat-page";
import { LoginPage } from "@/pages/login-page";

export function App(): JSX.Element {
  const { isAuthenticated } = useAuth();

  return (
    <Routes>
      <Route path="/login" element={isAuthenticated ? <Navigate to="/chat" replace /> : <LoginPage />} />

      <Route element={<ProtectedRoute />}>
        <Route element={<AppShell />}>
          <Route path="/chat" element={<ChatPage />} />
          <Route element={<RoleRoute allowedRoles={["admin"]} />}>
            <Route path="/admin" element={<AdminDashboardPage />} />
          </Route>
        </Route>
      </Route>

      <Route path="*" element={<Navigate to={isAuthenticated ? "/chat" : "/login"} replace />} />
    </Routes>
  );
}
