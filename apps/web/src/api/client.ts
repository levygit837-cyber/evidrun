import type { BackendConnection, DashboardData, ProviderProfile } from "../types";

let cachedConnection: BackendConnection | null = null;

async function connection(): Promise<BackendConnection> {
  if (cachedConnection) return cachedConnection;
  if (window.evidrunDesktop) {
    cachedConnection = await window.evidrunDesktop.getBackendConnection();
    return cachedConnection;
  }
  cachedConnection = { baseUrl: "", token: "", instanceId: "browser" };
  return cachedConnection;
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const backend = await connection();
  const headers = new Headers(init?.headers);
  headers.set("Content-Type", "application/json");
  if (backend.token) headers.set("Authorization", `Bearer ${backend.token}`);
  const response = await fetch(`${backend.baseUrl}${path}`, { ...init, headers });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`API ${response.status}: ${detail}`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  dashboard: () => apiFetch<DashboardData>("/api/v1/dashboard"),
  defaultProvider: () => apiFetch<ProviderProfile>("/api/v1/providers/default"),
  bootstrapDemo: () =>
    apiFetch<{ comparison_id: string }>("/api/v1/demo/bootstrap", { method: "POST" }),
  exportBundle: (comparisonId: string) =>
    apiFetch<{ path: string }>(`/api/v1/evidence-bundles/${comparisonId}`, { method: "POST" }),
};
