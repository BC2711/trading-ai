import { describe, expect, it, vi } from "vitest";

type RejectionHandler = (error: unknown) => Promise<unknown>;

type FakeAxiosClient = {
  defaults: { headers: { common: Record<string, string> } };
  interceptors: {
    request: { use: (handler: (config: RequestConfig) => RequestConfig) => void };
    response: { use: (_success: (response: unknown) => unknown, rejection: RejectionHandler) => void };
  };
  post: ReturnType<typeof vi.fn>;
  get: ReturnType<typeof vi.fn>;
  requestHandler?: (config: RequestConfig) => Promise<unknown>;
  requestInterceptor?: (config: RequestConfig) => RequestConfig;
  responseRejection?: RejectionHandler;
};

type RequestConfig = {
  url?: string;
  headers: Record<string, string>;
  _retry?: boolean;
};

const clients: FakeAxiosClient[] = [];

function createFakeClient(): FakeAxiosClient {
  const callable = vi.fn((config: RequestConfig) => fakeClient.requestHandler?.(config) ?? Promise.resolve({ data: "retried" }));
  const fakeClient = callable as unknown as FakeAxiosClient;
  fakeClient.defaults = { headers: { common: {} } };
  fakeClient.post = vi.fn();
  fakeClient.get = vi.fn();
  fakeClient.interceptors = {
    request: {
      use: vi.fn((handler: (config: RequestConfig) => RequestConfig) => {
        fakeClient.requestInterceptor = handler;
      })
    },
    response: {
      use: vi.fn((_success: (response: unknown) => unknown, rejection: RejectionHandler) => {
        fakeClient.responseRejection = rejection;
      })
    }
  };
  clients.push(fakeClient);
  return fakeClient;
}

function jwt(expOffsetSeconds: number) {
  const payload = btoa(JSON.stringify({ exp: Math.floor(Date.now() / 1000) + expOffsetSeconds }))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
  return `header.${payload}.signature`;
}

async function loadApiModule() {
  vi.resetModules();
  clients.length = 0;
  vi.doMock("axios", () => ({
    default: {
      create: vi.fn(createFakeClient)
    }
  }));
  return import("./api");
}

describe("auth API behavior", () => {
  it("stores access and refresh tokens after login", async () => {
    const api = await loadApiModule();
    const authClient = clients[1];
    authClient.post.mockResolvedValueOnce({
      data: { access_token: jwt(60), refresh_token: "refresh-token", token_type: "bearer" }
    });

    await api.login({ email: "trader@example.com", password: "secret-password" });

    expect(authClient.post).toHaveBeenCalledWith("/api/auth/login", {
      email: "trader@example.com",
      password: "secret-password"
    });
    expect(localStorage.getItem("trading_ai_token")).toContain("header.");
    expect(localStorage.getItem("trading_ai_refresh_token")).toBe("refresh-token");
    expect(api.apiClient.defaults.headers.common.Authorization).toMatch(/^Bearer header\./);
  });

  it("refreshes an expired response once and retries the protected request", async () => {
    const api = await loadApiModule();
    const apiClient = clients[0];
    const authClient = clients[1];
    localStorage.setItem("trading_ai_token", jwt(60));
    localStorage.setItem("trading_ai_refresh_token", "refresh-token");
    authClient.post.mockResolvedValueOnce({
      data: { access_token: jwt(120), refresh_token: "rotated-refresh", token_type: "bearer" }
    });
    const originalRequest: RequestConfig = { url: "/api/signals", headers: {} };
    apiClient.requestHandler = vi.fn().mockResolvedValue({ data: [{ symbol: "BTCUSDT" }] });

    const response = await apiClient.responseRejection?.({
      response: { status: 401 },
      config: originalRequest
    });

    expect(authClient.post).toHaveBeenCalledWith("/api/auth/refresh", { refresh_token: "refresh-token" });
    expect(originalRequest._retry).toBe(true);
    expect(originalRequest.headers.Authorization).toMatch(/^Bearer header\./);
    expect(apiClient).toHaveBeenCalledWith(originalRequest);
    expect(response).toEqual({ data: [{ symbol: "BTCUSDT" }] });
    expect(localStorage.getItem("trading_ai_refresh_token")).toBe("rotated-refresh");
  });

  it("clears local auth state on logout even when the request fails", async () => {
    const api = await loadApiModule();
    const apiClient = clients[0];
    localStorage.setItem("trading_ai_token", jwt(60));
    localStorage.setItem("trading_ai_refresh_token", "refresh-token");
    api.apiClient.defaults.headers.common.Authorization = "Bearer existing";
    apiClient.post.mockRejectedValueOnce(new Error("network down"));

    await api.logout();

    expect(apiClient.post).toHaveBeenCalledWith("/api/auth/logout");
    expect(localStorage.getItem("trading_ai_token")).toBeNull();
    expect(localStorage.getItem("trading_ai_refresh_token")).toBeNull();
    expect(api.apiClient.defaults.headers.common.Authorization).toBeUndefined();
  });
});
