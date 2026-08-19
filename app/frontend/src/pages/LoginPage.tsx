import { useState, type FormEvent } from "react";
import { Navigate } from "react-router-dom";
import { Activity, AlertCircle, Loader2, Lock, Mail } from "lucide-react";
import { useAuth } from "../auth/AuthContext";

const DEMO_ACCOUNTS = [
  { role: "Doctor", emails: ["sharma@cis.com", "verma@cis.com"] },
  { role: "Radiologist", emails: ["singh@cis.com", "iyer@cis.com"] },
  {
    role: "Patient",
    emails: ["aisha.khan@cis.com", "ravi.verma@cis.com", "meena.patel@cis.com", "john.fernandes@cis.com", "priya.nair@cis.com"],
  },
];

export function LoginPage() {
  const { user, login, loginError, loginPending } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [redirectTo, setRedirectTo] = useState<string | null>(null);

  if (user) {
    return <Navigate to={`/${user.role}`} replace />;
  }
  if (redirectTo) {
    return <Navigate to={redirectTo} replace />;
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    try {
      const loggedInUser = await login(email, password);
      setRedirectTo(`/${loggedInUser.role}`);
    } catch {
      // error surfaced via loginError below
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-brand-900 via-brand-800 to-slate-900 px-4">
      <div className="w-full max-w-md">
        <div className="mb-6 flex flex-col items-center text-center">
          <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-2xl bg-white shadow-lg">
            <Activity className="h-6 w-6 text-brand-600" />
          </div>
          <h1 className="text-2xl font-semibold text-white">Clinical Intelligence System</h1>
          <p className="mt-1 text-sm text-brand-200">AI-Driven Multi-Role Clinical Intelligence System</p>
        </div>

        <div className="rounded-2xl bg-white p-6 shadow-2xl sm:p-8">
          {loginError && (
            <div className="mb-4 flex items-start gap-2 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
              <span>{loginError}</span>
            </div>
          )}
          <form onSubmit={onSubmit} className="space-y-4">
            <div>
              <label htmlFor="email" className="mb-1 block text-sm font-medium text-slate-700">
                Email
              </label>
              <div className="relative">
                <Mail className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                <input
                  id="email"
                  type="email"
                  required
                  autoComplete="username"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 py-2 pl-9 pr-3 text-sm text-slate-900 outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
                  placeholder="you@cis.com"
                />
              </div>
            </div>
            <div>
              <label htmlFor="password" className="mb-1 block text-sm font-medium text-slate-700">
                Password
              </label>
              <div className="relative">
                <Lock className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                <input
                  id="password"
                  type="password"
                  required
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 py-2 pl-9 pr-3 text-sm text-slate-900 outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
                  placeholder="••••••••"
                />
              </div>
            </div>
            <button
              type="submit"
              disabled={loginPending}
              className="flex w-full items-center justify-center gap-2 rounded-lg bg-brand-600 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {loginPending && <Loader2 className="h-4 w-4 animate-spin" />}
              Sign in
            </button>
          </form>

          <div className="mt-6 rounded-lg bg-slate-50 p-3 text-xs text-slate-500">
            <p className="mb-1.5 font-medium text-slate-600">Seeded demo accounts (password: password123)</p>
            <ul className="space-y-1">
              {DEMO_ACCOUNTS.map((group) => (
                <li key={group.role}>
                  <span className="font-medium text-slate-600">{group.role}:</span> {group.emails.join(", ")}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
