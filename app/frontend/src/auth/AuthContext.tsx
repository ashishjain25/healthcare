import { createContext, useContext, type ReactNode } from "react";
import { useLogin, useLogout, useMe } from "../api/hooks";
import type { SessionUser } from "../api/types";

interface AuthContextValue {
  user: SessionUser | null | undefined;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<SessionUser>;
  loginError: string | null;
  loginPending: boolean;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const meQuery = useMe();
  const loginMutation = useLogin();
  const logoutMutation = useLogout();

  const value: AuthContextValue = {
    user: meQuery.data,
    isLoading: meQuery.isLoading,
    login: (email, password) => loginMutation.mutateAsync({ email, password }),
    loginError: loginMutation.error ? loginMutation.error.message : null,
    loginPending: loginMutation.isPending,
    logout: () => {
      logoutMutation.mutate(undefined, {
        onSuccess: () => {
          window.location.href = "/login";
        },
      });
    },
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
