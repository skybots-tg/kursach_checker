// Определяем базовый URL API
// В dev режиме используем proxy через vite, в production - абсолютный URL
// Можно переопределить через переменную окружения VITE_API_BASE при сборке
function getApiBase(): string {
  // Если задана переменная окружения - используем её
  if (import.meta.env.VITE_API_BASE) {
    return import.meta.env.VITE_API_BASE;
  }
  
  // В dev режиме используем относительный путь (работает через vite proxy)
  if (import.meta.env.MODE === 'development' || import.meta.env.DEV) {
    return '/api/admin';
  }
  
  // В production используем абсолютный URL
  // Если фронтенд и бэкенд на одном домене, можно использовать относительный путь
  // Но если на разных портах - нужен абсолютный URL
  const host = typeof window !== 'undefined' ? window.location.hostname : 'localhost';
  const port = '8343';
  return `http://${host}:${port}/api/admin`;
}

const API_BASE = getApiBase();

async function fetchApi<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  console.log(`[API] Fetching: ${url}`);
  
  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options?.headers,
      },
    });
    
    console.log(`[API] Response status: ${response.status} for ${url}`);
    
    if (!response.ok) {
      const errorText = await response.text();
      console.error(`[API] Error response:`, errorText);
      throw new Error(`API error (${response.status}): ${response.statusText}`);
    }
    
    const data = await response.json();
    console.log(`[API] Success for ${url}`);
    return data;
  } catch (error) {
    console.error(`[API] Fetch error for ${url}:`, error);
    throw error;
  }
}

export interface DashboardStats {
  checks_today: number;
  checks_7days: number;
  payments_today: number;
  payments_7days: number;
  avg_processing_time_seconds: number | null;
  worker_errors_recent: number;
}

export interface DashboardEvent {
  time: string;
  event: string;
  status: string;
}

export interface DashboardData {
  stats: DashboardStats;
  recent_events: DashboardEvent[];
}

export interface CheckItem {
  id: number;
  user_id: number;
  template_version_id: number;
  gost_id: number | null;
  status: string;
  created_at: string;
  finished_at: string | null;
  input_file_id: number;
  result_report_id: number | null;
  output_file_id: number | null;
}

export interface UserItem {
  id: number;
  telegram_id: number;
  username: string | null;
  first_name: string | null;
  credits_balance: number;
  created_at: string;
  last_login_at: string | null;
}

export interface ProductItem {
  id: number;
  name: string;
  price: number;
  currency: string;
  credits_amount: number;
  active: boolean;
  description: string | null;
  created_at: string;
}

export interface OrderItem {
  id: number;
  user_id: number;
  product_id: number;
  status: string;
  amount: number;
  created_at: string;
  paid_at: string | null;
}

export interface ProdamusPaymentItem {
  id: number;
  order_id: number;
  prodamus_invoice_id: string;
  status: string;
  raw_payload: Record<string, any>;
  created_at: string;
}

export interface AuditLogItem {
  id: number;
  admin_user_id: number | null;
  action: string;
  entity_type: string | null;
  entity_id: number | null;
  diff_json: Record<string, any> | null;
  created_at: string;
}

export interface UniversityItem {
  id: number;
  name: string;
  active: boolean;
  description: string | null;
  priority: number;
}

export interface GostItem {
  id: number;
  name: string;
  description: string | null;
  active: boolean;
  type: string | null;
  year: number | null;
}

export interface TemplateItem {
  id: number;
  university_id: number;
  name: string;
  type_work: string;
  year: number | null;
  status: string;
  active: boolean;
}

export const api = {
  getDashboard: () => fetchApi<DashboardData>("/dashboard"),
  
  getChecks: (search?: string, status?: string) => {
    const params = new URLSearchParams();
    if (search) params.append("search", search);
    if (status && status !== "Все") params.append("status_filter", status);
    return fetchApi<CheckItem[]>(`/checks?${params.toString()}`);
  },
  
  getUsers: (search?: string) => {
    const params = new URLSearchParams();
    if (search) params.append("search", search);
    return fetchApi<UserItem[]>(`/users?${params.toString()}`);
  },
  
  getProducts: () => fetchApi<ProductItem[]>("/products"),
  
  getOrders: () => fetchApi<OrderItem[]>("/orders"),
  
  getPaymentsProdamus: () => fetchApi<ProdamusPaymentItem[]>("/payments_prodamus"),
  
  getAuditLogs: () => fetchApi<AuditLogItem[]>("/audit_logs"),
  
  getUniversities: () => fetchApi<UniversityItem[]>("/universities"),
  
  getGosts: () => fetchApi<GostItem[]>("/gosts"),
  
  getTemplates: () => fetchApi<TemplateItem[]>("/templates"),
};

