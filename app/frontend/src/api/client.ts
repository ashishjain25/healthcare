export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function handle<T>(res: Response): Promise<T> {
  if (res.status === 401) {
    if (!window.location.pathname.startsWith("/login")) {
      window.location.href = "/login";
    }
    throw new ApiError("Not authenticated", 401);
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      // ignore — body wasn't JSON
    }
    throw new ApiError(detail, res.status);
  }
  if (res.status === 204) return null as T;
  return (await res.json()) as T;
}

export function apiGet<T>(url: string): Promise<T> {
  return fetch(url, { credentials: "same-origin" }).then((res) => handle<T>(res));
}

export function apiPostJson<T>(url: string, body: unknown): Promise<T> {
  return fetch(url, {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  }).then((res) => handle<T>(res));
}

export function apiPatchJson<T>(url: string, body: unknown): Promise<T> {
  return fetch(url, {
    method: "PATCH",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  }).then((res) => handle<T>(res));
}

export function apiPostForm<T>(url: string, formData: FormData): Promise<T> {
  return fetch(url, { method: "POST", credentials: "same-origin", body: formData }).then((res) =>
    handle<T>(res),
  );
}
