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
      // FastAPI's own request-validation errors (missing/invalid form
      // fields) shape `detail` as a list of {loc, msg, ...} objects rather
      // than a string — stringifying that directly renders as
      // "[object Object]". Our own handlers always raise a string detail,
      // so only this automatic-validation shape needs special-casing.
      if (typeof body.detail === "string") {
        detail = body.detail;
      } else if (Array.isArray(body.detail)) {
        detail = body.detail.map((e: { msg?: string }) => e?.msg).filter(Boolean).join("; ") || detail;
      } else if (body.detail) {
        detail = JSON.stringify(body.detail);
      }
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
