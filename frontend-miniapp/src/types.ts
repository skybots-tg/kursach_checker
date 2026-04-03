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
  university_id: number;
  name: string;
  type_work: string;
  year: string;
  status: string;
  active: boolean;
  latest_version_id: number | null;
}

export interface CheckReportFinding {
  title: string;
  severity: "error" | "warning" | "advice" | "info";
  category: string;
  auto_fixed: boolean;
  expected: string | null;
  found: string | null;
  recommendation: string | null;
  location: string | null;
  auto_fix_details?: string;
}

export interface CheckReport {
  findings: CheckReportFinding[];
  summary_errors: number;
  summary_warnings: number;
  summary_autofixed: number;
}

export interface CheckDetailResponse {
  id: number;
  status: string;
  created_at: string;
  finished_at: string | null;
  report_file_id: number | null;
  output_file_id: number | null;
  report: CheckReport | null;
}

export interface CheckItem {
  id: number;
  status: string;
  created_at: string;
  finished_at: string | null;
  template_version_id: number;
  result_report_file_id: number | null;
  output_file_id: number | null;
}

export interface OrderItem {
  id: number;
  amount: number;
  status: string;
  product: string;
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

export interface UploadResult {
  file_id: number;
  filename: string;
  size: number;
}

export interface StartCheckResult {
  id: number;
  status: string;
}

export interface CreatePaymentResult {
  order_id: number;
  payment_url: string;
}
