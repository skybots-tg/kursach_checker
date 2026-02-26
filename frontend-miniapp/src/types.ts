export interface SessionResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface MeResponse {
  id: number;
  telegram_id: number;
  first_name: string | null;
  username: string | null;
  credits_available: number;
}

export interface UniversityItem {
  id: number;
  name: string;
  active: boolean;
}

export interface GostItem {
  id: number;
  name: string;
  description: string | null;
  active: boolean;
}

export interface TemplateItem {
  id: number;
  name: string;
  type_work: string;
  year: number | null;
}

export interface PaymentCreateResponse {
  payment_url: string;
  order_id: number;
}

export interface OrderItem {
  id: number;
  status: string;
  amount: number;
  created_at: string;
  paid_at: string | null;
}

export interface ProductItem {
  id: number;
  name: string;
  price: number;
  currency: string;
  credits_amount: number;
  description: string | null;
}

export interface CheckItem {
  id: number;
  status: string;
  template_version_id: number;
  gost_id: number | null;
  created_at: string;
  finished_at: string | null;
}

export interface CheckReportFinding {
  rule_id: string;
  title: string;
  category: string;
  severity: "error" | "warning" | "info" | "advice" | string;
  expected: string | null;
  actual: string | null;
  recommendation: string | null;
  location: {
    section_id: string | null;
    section_title: string | null;
    page: number | null;
    paragraph_index: number | null;
  } | null;
  auto_fixed: boolean;
  auto_fix_description: string | null;
}

export interface CheckReport {
  template_profile_id?: string;
  template_version_id?: number;
  summary_errors?: number;
  summary_warnings?: number;
  summary_autofixed?: number;
  findings?: CheckReportFinding[];
  [key: string]: unknown;
}

export interface CheckDetailResponse {
  id: number;
  status: string;
  report: CheckReport | null;
  output_file_id: number | null;
}

export interface FileUploadResponse {
  file_id: number;
  original_name: string;
  mime: string;
  size: number;
}



