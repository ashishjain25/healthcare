import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "./AuthContext";
import type { Role } from "../api/types";

export function ProtectedRoute({ role, children }: { role: Role; children: ReactNode }) {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-slate-50">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" />
      </div>
    );
  }

  if (!user || user.role !== role) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}
