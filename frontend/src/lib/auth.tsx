import { createContext, createElement, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api, clearTokens, setTokens, type AuthUser } from "./api";

type AuthState = {
  user: AuthUser | null;
  loading: boolean;
  login: (identifier: string, password: string) => Promise<AuthUser>;
  register: (payload: Record<string, string>) => Promise<void>;
  logout: () => Promise<void>;
  can: (module: string, action: string) => boolean;
};

const Ctx = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const tok = localStorage.getItem("cl_access");
    if (!tok) {
      setLoading(false);
      return;
    }
    api<AuthUser>("/api/v1/auth/me")
      .then(setUser)
      .catch(() => {
        clearTokens();
        setUser(null);
      })
      .finally(() => setLoading(false));
  }, []);

  const value = useMemo<AuthState>(
    () => ({
      user,
      loading,
      async login(identifier, password) {
        const data = await api<{ accessToken: string; refreshToken: string; user: AuthUser }>("/api/v1/auth/login", {
          method: "POST",
          body: JSON.stringify({ identifier, password }),
        });
        setTokens(data.accessToken, data.refreshToken);
        setUser(data.user);
        return data.user;
      },
      async register(payload) {
        await api("/api/v1/auth/register", { method: "POST", body: JSON.stringify(payload) });
      },
      async logout() {
        try {
          await api("/api/v1/auth/logout", {
            method: "POST",
            body: JSON.stringify({ refresh_token: localStorage.getItem("cl_refresh") }),
          });
        } catch {
          /* still clear locally */
        }
        clearTokens();
        setUser(null);
      },
      can(module, action) {
        return Boolean(user?.permissions.some((p) => p.module === module && p.action === action && p.allowed));
      },
    }),
    [user, loading],
  );

  return createElement(Ctx.Provider, { value }, children);
}

export function useAuth() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("AuthProvider missing");
  return ctx;
}

export function dashboardPath(role?: string) {
  switch (role) {
    case "ADMIN":
      return "/app/admin";
    case "NAGAR_SEVAK":
      return "/app/ward";
    case "OFFICER":
      return "/app/officer";
    case "ENGINEER":
      return "/app/engineer";
    case "CONTRACTOR":
      return "/app/contractor";
    default:
      return "/app";
  }
}
