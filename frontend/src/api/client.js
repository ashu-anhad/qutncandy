// Thin fetch wrapper: attaches the access token, and on a 401 refreshes it once via the
// httpOnly refresh cookie before retrying. The access token lives only in memory.
let accessToken = null;
let refreshInFlight = null;
let onSessionLost = () => {};

export const setAccessToken = (token) => {
  accessToken = token;
};
export const setSessionLostHandler = (fn) => {
  onSessionLost = fn;
};

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

async function parseError(res) {
  const body = await res.json().catch(() => ({}));
  const detail = Array.isArray(body.detail) ? body.detail.map((d) => d.msg).join(", ") : body.detail;
  return new ApiError(detail || `Request failed (${res.status})`, res.status);
}

// Returns { access_token, user } or null. Concurrent callers share one request.
export function refreshSession() {
  refreshInFlight ??= fetch("/api/auth/refresh", { method: "POST" })
    .then(async (res) => {
      if (!res.ok) return null;
      const data = await res.json();
      setAccessToken(data.access_token);
      return data;
    })
    .catch(() => null)
    .finally(() => {
      refreshInFlight = null;
    });
  return refreshInFlight;
}

async function request(method, path, body, retry = true) {
  const isForm = body instanceof FormData;
  const headers = {};
  if (body !== undefined && !isForm) headers["Content-Type"] = "application/json";
  if (accessToken) headers.Authorization = `Bearer ${accessToken}`;

  const res = await fetch(path, {
    method,
    headers,
    body: body === undefined || isForm ? body : JSON.stringify(body),
  });

  if (res.status === 401 && retry && !path.startsWith("/api/auth/")) {
    if (await refreshSession()) return request(method, path, body, false);
    setAccessToken(null);
    onSessionLost();
  }
  if (!res.ok) throw await parseError(res);
  return res.status === 204 ? null : res.json();
}

// Authenticated file download (e.g. CSV reports): saves the response as `filename`.
export async function download(path, filename, retry = true) {
  const res = await fetch(path, { headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {} });
  if (res.status === 401 && retry && (await refreshSession())) return download(path, filename, false);
  if (!res.ok) throw await parseError(res);
  const url = URL.createObjectURL(await res.blob());
  const a = Object.assign(document.createElement("a"), { href: url, download: filename });
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export const api = {
  get: (path) => request("GET", path),
  post: (path, body) => request("POST", path, body),
  patch: (path, body) => request("PATCH", path, body),
  put: (path, body) => request("PUT", path, body),
  del: (path) => request("DELETE", path),
  upload: (path, formData) => request("POST", path, formData),
};
