import type {
  MeResponse,
  UniversityItem,
  GostItem,
  TemplateItem,
  ProductItem,
  OrderItem,
  CheckItem,
  CheckDetailResponse,
  FileUploadResponse,
  SessionResponse,
  PaymentCreateResponse
} from "./types";

const MINIAPP_BASE = "/api/miniapp";
const TOKEN_KEY = "miniapp_access_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...(options.headers || {})
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${MINIAPP_BASE}${path}`, {
    ...options,
    headers
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(text || `Request failed with status ${res.status}`);
  }
  if (res.status === 204) {
    return undefined as unknown as T;
  }
  return (await res.json()) as T;
}

export async function authWithTelegram(initData: string): Promise<SessionResponse> {
  const res = await request<SessionResponse>("/auth/telegram", {
    method: "POST",
    body: JSON.stringify({ init_data: initData })
  });
  setToken(res.access_token);
  return res;
}

export function fetchMe(): Promise<MeResponse> {
  return request<MeResponse>("/me");
}

export function fetchUniversities(): Promise<UniversityItem[]> {
  return request<UniversityItem[]>("/universities");
}

export function fetchGosts(): Promise<GostItem[]> {
  return request<GostItem[]>("/gosts");
}

export function fetchTemplates(universityId?: number): Promise<TemplateItem[]> {
  const q = universityId ? `?university_id=${universityId}` : "";
  return request<TemplateItem[]>(`/templates${q}`);
}

export function fetchProducts(): Promise<ProductItem[]> {
  return request<ProductItem[]>("/products");
}

export function createPayment(productId: number): Promise<PaymentCreateResponse> {
  return request<PaymentCreateResponse>("/payments/create", {
    method: "POST",
    body: JSON.stringify({ product_id: productId })
  });
}

export function fetchOrders(): Promise<OrderItem[]> {
  return request<OrderItem[]>("/orders");
}

export function fetchChecks(): Promise<CheckItem[]> {
  return request<CheckItem[]>("/checks");
}

export function fetchCheckDetail(id: number): Promise<CheckDetailResponse> {
  return request<CheckDetailResponse>(`/checks/${id}`);
}

export function fetchDemoCheck(): Promise<CheckDetailResponse> {
  return request<CheckDetailResponse>("/demo/check");
}

export async function uploadFile(file: File): Promise<FileUploadResponse> {
  const token = getToken();
  if (!token) {
    throw new Error("Not authenticated");
  }
  const form = new FormData();
  form.append("upload", file);
  const res = await fetch(`${MINIAPP_BASE}/files/upload`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`
    },
    body: form
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(text || `Upload failed with status ${res.status}`);
  }
  return (await res.json()) as FileUploadResponse;
}

export function startCheck(payload: {
  template_version_id: number;
  gost_id: number | null;
  file_id: number;
}): Promise<CheckItem> {
  return request<CheckItem>("/checks/start", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}




