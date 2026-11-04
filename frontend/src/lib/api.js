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

export function buildWsUrl(path) {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  let baseWsUrl = import.meta.env.VITE_WS_URL;
  if (!baseWsUrl) {
    const loc = window.location;
    baseWsUrl = (loc.protocol === "https:" ? "wss://" : "ws://") + loc.host;
  }
  return `${baseWsUrl.replace(/\/+$/, "")}${normalizedPath}`;
}
