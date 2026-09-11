const API = import.meta.env.VITE_API_URL || "";

export type Perm = { module: string; action: string; scope: string; allowed: boolean };

export type AuthUser = {
  id: string;
  fullName: string;
  email: string;
  mobile?: string | null;
  role: string;
  isDemo: boolean;
  assignedWardId?: string | null;
  assignedWardName?: string | null;
  assignedDepartmentId?: string | null;
  assignedDepartmentName?: string | null;
  permissions: Perm[];
};

function accessToken() {
  return localStorage.getItem("cl_access");
}

export function setTokens(access: string, refresh: string) {
  localStorage.setItem("cl_access", access);
  localStorage.setItem("cl_refresh", refresh);
}

export function clearTokens() {
  localStorage.removeItem("cl_access");
  localStorage.removeItem("cl_refresh");
}

async function refreshTokens() {
  const refresh = localStorage.getItem("cl_refresh");
  if (!refresh) throw new Error("No refresh token");
  const res = await fetch(`${API}/api/v1/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refresh }),
  });
  if (!res.ok) throw new Error("Refresh failed");
  const data = await res.json();
  setTokens(data.accessToken, data.refreshToken);
  return data;
}

export async function api<T = unknown>(path: string, init: RequestInit = {}, retry = true): Promise<T> {
  const headers = new Headers(init.headers);
  if (!(init.body instanceof FormData) && !headers.has("Content-Type") && init.body) {
    headers.set("Content-Type", "application/json");
  }
  const tok = accessToken();
  if (tok) headers.set("Authorization", `Bearer ${tok}`);
  const res = await fetch(`${API}${path}`, { ...init, headers });
  if (res.status === 401 && retry && localStorage.getItem("cl_refresh")) {
    try {
      await refreshTokens();
      return api<T>(path, init, false);
    } catch {
      clearTokens();
      window.location.href = "/login";
      throw new Error("Session expired");
    }
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const msg = data?.error?.message || res.statusText;
    const err = new Error(msg) as Error & { status: number };
    err.status = res.status;
    throw err;
  }
  return data as T;
}
