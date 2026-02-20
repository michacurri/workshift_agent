/** API response types aligned with backend schemas */

export interface RuleEngineResult {
  valid: boolean;
  errorCodes: string[];
  reason?: string;
  suggestions: Record<string, unknown>[];
  validationDetails: Record<string, unknown>;
}

export interface ScheduleRequestOut {
  requestId: string;
  status: string;
  extractionVersion?: string;
  parsed?: Record<string, unknown>;
  validation: RuleEngineResult;
  approvalId?: string;
  correlationId: string;
  idempotentHit?: boolean;
  summary?: string | null;
}

export interface PreviewResponse {
  parsed: Record<string, unknown>;
  validation: RuleEngineResult;
  summary: string;
  needsInput?: { field: string; prompt: string; options?: string[] | null }[];
}

export interface PartnerPendingItem {
  requestId: string;
  summary: string;
  requester_full_name?: string | null;
  requester_shift_date?: string | null;
  requester_shift_type?: string | null;
  partner_shift_date?: string | null;
  partner_shift_type?: string | null;
  submittedAt: string;
  workload_shifts_this_week?: number | null;
}

export interface PendingApprovalItem {
  requestId: string;
  submittedAt: string;
  parsed: Record<string, unknown>;
  requested_action?: string | null;
  requester_full_name?: string | null;
  requester_shift_date?: string | null;
  requester_shift_type?: string | null;
  partner_full_name?: string | null;
  partner_shift_date?: string | null;
  partner_shift_type?: string | null;
  result_summary?: string | null;
  urgent?: boolean;
}

export interface MetricsOut {
  total_requests: number;
  approval_rate: number;
  average_processing_time: number;
  parse_time_avg: number;
  validation_time_avg: number;
  approval_latency_avg: number;
}

export interface ShiftItem {
  id: string;
  date: string;
  type: "morning" | "night";
  required_skills: Record<string, unknown>;
  assigned_employee_id?: string | null;
  assigned_employee_full_name?: string | null;
}

export interface ShiftsResponse {
  shifts: ShiftItem[];
}

export interface ShiftCandidateOut {
  employee_id: string;
  full_name: string;
  reason: string;
  shifts_this_week: number;
}

export interface ScheduleRequestListItem {
  requestId: string;
  status: string;
  summary?: string | null;
  created_at: string;
  requester_full_name?: string | null;
  coverage_shift_id?: string | null;
  urgent?: boolean;
}

export interface EmployeeOut {
  id: string;
  full_name: string;
  first_name: string;
  last_name: string;
  role: "employee" | "admin";
  certifications: Record<string, unknown>;
  skills: Record<string, unknown>;
  availability: Record<string, unknown>;
}

export interface StructuredRequestIn {
  employee_first_name: string;
  employee_last_name?: string | null;
  current_shift_date?: string | null;
  current_shift_type?: "morning" | "night" | null;
  target_date?: string | null;
  target_shift_type?: "morning" | "night" | null;
  requested_action?: "swap" | "move" | "cover" | null;
  reason?: string | null;
  partner_employee_first_name?: string | null;
  partner_employee_last_name?: string | null;
  partner_shift_date?: string | null;
  partner_shift_type?: "morning" | "night" | null;
}
