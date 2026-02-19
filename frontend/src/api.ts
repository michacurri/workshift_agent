import type {
  EmployeeOut,
  MetricsOut,
  PartnerPendingItem,
  PendingApprovalItem,
  PreviewResponse,
  ScheduleRequestListItem,
  ScheduleRequestOut,
  ShiftsResponse,
  ShiftCandidateOut,
  StructuredRequestIn,
  RuleEngineResult,
} from "./types";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

interface ApiErrorBody {
  userMessage?: string;
  developerMessage?: string;
}

function getCurrentEmployeeId(): string | null {
  try {
    const stored = window.localStorage.getItem("currentUser");
    if (!stored) return null;
    const parsed = JSON.parse(stored) as { id?: string };
    return parsed.id ?? null;
  } catch {
    return null;
  }
}

async function call<T>(path: string, options: RequestInit = {}): Promise<T> {
  const currentEmployeeId = typeof window !== "undefined" ? getCurrentEmployeeId() : null;
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(currentEmployeeId ? { "X-Employee-Id": currentEmployeeId } : {}),
      ...(options.headers as HeadersInit),
    },
    ...options,
  });
  const data = (await response.json().catch(() => ({}))) as ApiErrorBody & T;
  if (!response.ok) {
    throw new Error(
      (data as ApiErrorBody).userMessage ||
        (data as ApiErrorBody).developerMessage ||
        "Request failed"
    );
  }
  return data as T;
}

export function submitRequest(text: string): Promise<ScheduleRequestOut> {
  return call<ScheduleRequestOut>("/schedule/request", {
    method: "POST",
    body: JSON.stringify({ text }),
  });
}

export function getPendingApprovals(): Promise<PendingApprovalItem[]> {
  return call<PendingApprovalItem[]>("/approval/pending");
}

export function approveRequest(id: string): Promise<{ requestId: string; status: string; correlationId: string }> {
  return call(`/approval/${id}/approve`, { method: "POST" });
}

export function rejectRequest(id: string): Promise<{ requestId: string; status: string; correlationId: string }> {
  return call(`/approval/${id}/reject`, { method: "POST" });
}

export function getPartnerPending(): Promise<PartnerPendingItem[]> {
  return call<PartnerPendingItem[]>("/partner/pending");
}

export function partnerAccept(requestId: string): Promise<{ requestId: string; status: string }> {
  return call(`/partner/${requestId}/accept`, { method: "POST" });
}

export function partnerReject(requestId: string): Promise<{ requestId: string; status: string }> {
  return call(`/partner/${requestId}/reject`, { method: "POST" });
}

export function getMetrics(): Promise<MetricsOut> {
  return call<MetricsOut>("/metrics");
}

export function getScheduleRequests(): Promise<ScheduleRequestListItem[]> {
  return call<ScheduleRequestListItem[]>("/schedule/requests");
}

export function getShifts(from: string, to: string, employeeId?: string): Promise<ShiftsResponse> {
  const params = new URLSearchParams({ from, to });
  if (employeeId) {
    params.set("employee_id", employeeId);
  }
  return call<ShiftsResponse>(`/schedule/shifts?${params.toString()}`);
}

export function getShiftCandidates(shiftId: string): Promise<ShiftCandidateOut[]> {
  return call<ShiftCandidateOut[]>(`/schedule/shifts/${shiftId}/candidates`);
}

export function assignShift(shiftId: string, employeeId: string): Promise<{ shiftId: string; assignedEmployeeId: string }> {
  return call(`/schedule/shifts/${shiftId}/assign`, {
    method: "POST",
    body: JSON.stringify({ employee_id: employeeId }),
  });
}

/** Unified preview: pass either { text } or { structured } */
export function previewUnified(payload: { text?: string; structured?: StructuredRequestIn }): Promise<PreviewResponse> {
  return call<PreviewResponse>("/schedule/preview", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function previewStructured(body: StructuredRequestIn): Promise<PreviewResponse> {
  return previewUnified({ structured: body });
}

export function submitStructured(body: StructuredRequestIn): Promise<ScheduleRequestOut> {
  return call<ScheduleRequestOut>("/schedule/request/structured", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function getEmployees(): Promise<EmployeeOut[]> {
  return call<EmployeeOut[]>("/employees");
}

export function createEmployee(body: Omit<EmployeeOut, "id" | "full_name">): Promise<EmployeeOut> {
  return call<EmployeeOut>("/employees", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function updateEmployee(id: string, body: Partial<Omit<EmployeeOut, "id" | "full_name">>): Promise<EmployeeOut> {
  return call<EmployeeOut>(`/employees/${id}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export function deleteEmployee(id: string): Promise<void> {
  return call<void>(`/employees/${id}`, {
    method: "DELETE",
  });
}
