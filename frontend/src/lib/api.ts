import axios from "axios";
import { useAuthStore } from "@/store/auth-store";

function normalizeApiBaseUrl(value?: string) {
  const baseUrl = (value || "http://localhost:8000").replace(/\/$/, "");
  return baseUrl.endsWith("/api") ? baseUrl : `${baseUrl}/api`;
}

export const api = axios.create({
  baseURL: normalizeApiBaseUrl(process.env.NEXT_PUBLIC_API_BASE_URL),
  timeout: 10_000,
  headers: {
    "Content-Type": "application/json",
  },
});

api.interceptors.request.use((config) => {
  const accessToken = useAuthStore.getState().accessToken;

  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`;
  }

  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config as
      | (typeof error.config & { _retry?: boolean })
      | undefined;
    const refreshToken = useAuthStore.getState().refreshToken;

    if (
      error.response?.status === 401 &&
      originalRequest &&
      !originalRequest._retry &&
      refreshToken &&
      !originalRequest.url?.includes("/auth/refresh/")
    ) {
      originalRequest._retry = true;

      try {
        const response = await axios.post<{ access: string }>(
          `${api.defaults.baseURL}/auth/refresh/`,
          { refresh: refreshToken },
          {
            headers: { "Content-Type": "application/json" },
            timeout: 10_000,
          }
        );

        useAuthStore.getState().setTokens({
          accessToken: response.data.access,
          refreshToken,
        });

        originalRequest.headers = originalRequest.headers ?? {};
        originalRequest.headers.Authorization = `Bearer ${response.data.access}`;

        return api(originalRequest);
      } catch (refreshError) {
        useAuthStore.getState().clearSession();
        error = refreshError;
      }
    }

    const message =
      error.response?.data?.detail ||
      error.response?.data?.message ||
      error.message ||
      "Something went wrong while calling the API.";

    return Promise.reject(new Error(message));
  }
);
