import { Navigate, Outlet } from "react-router-dom";
import { dashboardPath, useAuth } from "../lib/auth";

export function RequireAuth({ roles }: { roles?: string[] }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="p-10 text-slate-400">Verifying session…</div>;
  if (!user) return <Navigate to="/login" replace />;
  if (roles && !roles.includes(user.role)) {
    return <Navigate to={dashboardPath(user.role)} replace />;
  }
  return <Outlet />;
}

export function GuestOnly() {
  const { user, loading } = useAuth();
  if (loading) return null;
  if (user) return <Navigate to={dashboardPath(user.role)} replace />;
  return <Outlet />;
}
