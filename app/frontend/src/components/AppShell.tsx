import type { ReactNode } from "react";
import { Activity, LogOut } from "lucide-react";
import { useAuth } from "../auth/AuthContext";

export function AppShell({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle: string;
  children: ReactNode;
}) {
  const { user, logout } = useAuth();

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="sticky top-0 z-10 border-b border-slate-200 bg-white/90 backdrop-blur">
        <div className="mx-auto flex max-w-[1600px] items-center justify-between gap-4 px-4 py-3 sm:px-6">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-600 text-white">
              <Activity className="h-5 w-5" />
            </div>
            <div>
              <p className="text-[10px] font-bold uppercase tracking-wider text-brand-600">
                Clinical Intelligence System
              </p>
              <h1 className="text-sm font-semibold leading-tight text-slate-900 sm:text-base">{title}</h1>
              <p className="hidden text-xs text-slate-500 sm:block">{subtitle}</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="hidden text-right sm:block">
              <p className="text-sm font-medium text-slate-800">{user?.full_name}</p>
              <p className="text-xs capitalize text-slate-400">{user?.role}</p>
            </div>
            <button
              onClick={logout}
              className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm font-medium text-slate-600 transition hover:border-red-200 hover:bg-red-50 hover:text-red-600"
            >
              <LogOut className="h-4 w-4" />
              <span className="hidden sm:inline">Log out</span>
            </button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-[1600px] px-4 py-6 sm:px-6">{children}</main>
    </div>
  );
}
