const rawBaseUrl = import.meta.env.VITE_API_URL || "/api";
const API_BASE_URL = rawBaseUrl.replace(/\/+$/, "");

export function apiFetch(path, options = {}) {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;

  return fetch(`${API_BASE_URL}${normalizedPath}`, {
    ...options,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });
}
