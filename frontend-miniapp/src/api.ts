import type {
  CheckDetailResponse,
  CheckItem,
  CreatePaymentResult,
  GostItem,
  MeResponse,
  OrderItem,
  ProductItem,
  StartCheckResult,
  TemplateItem,
  UniversityItem,
  UploadResult,
} from "./types";

const API_BASE = "/api";

let _token: string | null = null;

export function getToken(): string | null {
  if (!_token) {
    _token = sessionStorage.getItem("access_token");
  }
  return _token;
}

function setToken(token: string) {
  _token = token;
  sessionStorage.setItem("access_token", token);
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    ...(init?.headers as Record<string, string>),
  };

  const token = getToken();
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  if (!(init?.body instanceof FormData) && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }

  const res = await fetch(`${API_BASE}${path}`, { ...init, headers });

  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      if (body.detail) detail = body.detail;
    } catch { /* ignore */ }
    throw new Error(detail);
  }

  return res.json() as Promise<T>;
}

export async function authWithTelegram(initData: string): Promise<void> {
  const data = await request<{ access_token: string }>("/auth/telegram", {
    method: "POST",
    body: JSON.stringify({ init_data: initData }),
  });
  setToken(data.access_token);
}

export async function fetchMe(): Promise<MeResponse> {
  return request<MeResponse>("/auth/me");
}

export async function fetchUniversities(): Promise<UniversityItem[]> {
  return request<UniversityItem[]>("/universities");
}

export async function fetchGosts(): Promise<GostItem[]> {
  return request<GostItem[]>("/gosts");
}

export async function fetchTemplates(universityId: number): Promise<TemplateItem[]> {
  return request<TemplateItem[]>(`/templates?university_id=${universityId}`);
}

export async function uploadFile(file: File): Promise<UploadResult> {
  const form = new FormData();
  form.append("file", file);
  return request<UploadResult>("/checks/upload", {
    method: "POST",
    body: form,
  });
}

export async function startCheck(params: {
  template_version_id: number;
  gost_id: number | null;
  file_id: number;
}): Promise<StartCheckResult> {
  const qs = new URLSearchParams({
    template_version_id: String(params.template_version_id),
    input_file_id: String(params.file_id),
  });
  if (params.gost_id != null) {
    qs.set("gost_id", String(params.gost_id));
  }
  const data = await request<{ check_id: number; status: string }>(
    `/checks/start?${qs.toString()}`,
    { method: "POST" },
  );
  return { id: data.check_id, status: data.status };
}

export async function fetchCheckDetail(checkId: number): Promise<CheckDetailResponse> {
  return request<CheckDetailResponse>(`/checks/${checkId}`);
}

export async function fetchChecks(): Promise<CheckItem[]> {
  return request<CheckItem[]>("/checks");
}

export async function fetchOrders(): Promise<OrderItem[]> {
  return request<OrderItem[]>("/orders");
}

export async function fetchProducts(): Promise<ProductItem[]> {
  return request<ProductItem[]>("/products");
}

export async function createPayment(productId: number): Promise<CreatePaymentResult> {
  return request<CreatePaymentResult>("/payments/create", {
    method: "POST",
    body: JSON.stringify({ product_id: productId }),
  });
}

export async function fetchDemoCheck(): Promise<CheckDetailResponse> {
  return request<CheckDetailResponse>("/demo");
}
