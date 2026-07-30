const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export interface Camera {
  id: string;
  name: string;
  manufacturer: string;
  model: string | null;
  ip_address: string;
  onvif_port: number;
  rtsp_url: string;
  location_label: string | null;
  is_active: boolean;
  last_seen_at: string | null;
}

export interface Student {
  id: string;
  student_number: string;
  full_name: string;
  program: string | null;
  photo_path: string | null;
  is_active: boolean;
  created_at: string | null;
}

export interface AccessLogEntry {
  id: string;
  student_id: string | null;
  student_name: string | null;
  camera_id: string;
  camera_name: string | null;
  confidence_score: number | null;
  status: "GRANTED" | "DENIED";
  note: string | null;
  timestamp: string;
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      Accept: "application/json",
      ...(options.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...options.headers,
    },
  });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      // ignore parse errors
    }
    throw new Error(detail);
  }

  if (res.status === 204) {
    return undefined as unknown as T;
  }
  return res.json() as Promise<T>;
}

export const api = {
  cameras: {
    list: () => request<Camera[]>("/api/cameras"),
    discover: () => request<Camera[]>("/api/cameras/discover"),
    toggle: (id: string, active: boolean) =>
      request<Camera>(`/api/cameras/${id}/toggle?active=${active}`, { method: "PATCH" }),
    addManual: (payload: {
      name: string;
      nvr_ip: string;
      channel: number;
      username: string;
      password: string;
      port?: number;
      main_stream?: boolean;
      location_label?: string;
    }) =>
      request<Camera>("/api/cameras/manual", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
  },
  students: {
    list: () => request<Student[]>("/api/students"),
    enroll: (formData: FormData) =>
      request<Student>("/api/students/enroll", { method: "POST", body: formData }),
    deactivate: (id: string) => request<void>(`/api/students/${id}`, { method: "DELETE" }),
  },
  logs: {
    list: (limit = 100) => request<AccessLogEntry[]>(`/api/logs?limit=${limit}`),
  },
};

export function liveLogsSocketUrl(): string {
  const wsBase = API_BASE.replace(/^http/, "ws");
  return `${wsBase}/api/logs/live`;
}
