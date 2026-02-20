import { useEffect, useMemo, useState } from "react";
import { getShifts, previewStructured, previewUnified, submitStructured } from "../api";
import type { ShiftItem, StructuredRequestIn } from "../types";

const SHIFT_TYPES = ["morning", "night"] as const;
type ShiftType = (typeof SHIFT_TYPES)[number];

const ORG_TZ = "America/Toronto";

/** Format a date as YYYY-MM-DD in org timezone (Toronto). Avoids UTC rollover. */
function toOrgISODate(d: Date): string {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: ORG_TZ,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(d);
  const y = parts.find((p) => p.type === "year")?.value ?? "";
  const m = parts.find((p) => p.type === "month")?.value ?? "";
  const day = parts.find((p) => p.type === "day")?.value ?? "";
  return `${y}-${m}-${day}`;
}

/** Add n days to an ISO date string (YYYY-MM-DD), return ISO string in org timezone. */
function addDaysToISODate(iso: string, n: number): string {
  const parts = iso.split("-").map(Number);
  const y = parts[0] ?? 0;
  const m = (parts[1] ?? 1) - 1;
  const d = parts[2] ?? 1;
  const t = Date.UTC(y, m, d) + n * 24 * 60 * 60 * 1000;
  return toOrgISODate(new Date(t));
}

function getNextNDays(fromISODate: string, days: number): string[] {
  const dates: string[] = [];
  for (let i = 0; i < days; i += 1) {
    dates.push(addDaysToISODate(fromISODate, i));
  }
  return dates;
}

const initialForm: StructuredRequestIn = {
  employee_first_name: "",
  employee_last_name: "",
  current_shift_date: "",
  current_shift_type: "morning",
  target_date: "",
  target_shift_type: "morning",
  requested_action: "move",
  partner_employee_first_name: "",
  partner_employee_last_name: "",
  partner_shift_date: "",
  partner_shift_type: "morning",
  reason: "",
};

export type PreviewResult = {
  parsed: Record<string, unknown>;
  validation: { valid: boolean; errorCodes: string[]; reason?: string };
  summary?: string;
  needsInput?: { field: string; prompt: string; options?: string[] | null }[];
};

export default function useShiftBoardHook() {
  const today = useMemo(() => new Date(), []);
  const from = useMemo(() => toOrgISODate(today), [today]);
  const days = 7;
  const dates = useMemo(() => getNextNDays(from, days), [from, days]);

  const [shifts, setShifts] = useState<ShiftItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [form, setForm] = useState<StructuredRequestIn>(initialForm);
  const [previewResult, setPreviewResult] = useState<PreviewResult | null>(null);
  const [previewError, setPreviewError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function load() {
    setLoading(true);
    setError("");
    try {
      const to = dates[dates.length - 1] ?? from;
      const data = await getShifts(from, to);
      setShifts(data.shifts);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load shifts");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  function setTargetFromCell(dateStr: string, type: ShiftType) {
    setForm((prev) => ({
      ...prev,
      target_date: dateStr,
      target_shift_type: type,
    }));
  }

  function shiftsFor(dateStr: string, type: ShiftType) {
    return shifts.filter((s) => s.date === dateStr && s.type === type);
  }

  async function onPreview(e: React.FormEvent) {
    e.preventDefault();
    setPreviewError("");
    setPreviewResult(null);
    try {
      const result = await previewStructured(form);
      setPreviewResult({
        parsed: result.parsed,
        validation: {
          valid: result.validation.valid,
          errorCodes: result.validation.errorCodes,
          reason: result.validation.reason,
        },
        summary: result.summary,
        needsInput: result.needsInput,
      });
    } catch (err) {
      setPreviewError(err instanceof Error ? err.message : "Preview failed");
    }
  }

  function setFormFromParsed(parsed: Record<string, unknown>) {
    const shiftType = (v: unknown): StructuredRequestIn["target_shift_type"] => (v === "morning" || v === "night" ? v : "morning");
    const action = (v: unknown): StructuredRequestIn["requested_action"] => (v === "move" || v === "swap" || v === "cover" ? v : "move");
    setForm({
      employee_first_name: (parsed.employee_first_name as string) ?? "",
      employee_last_name: (parsed.employee_last_name as string) ?? "",
      current_shift_date: (parsed.current_shift_date as string) ?? "",
      current_shift_type: shiftType(parsed.current_shift_type),
      target_date: (parsed.target_date as string) ?? "",
      target_shift_type: shiftType(parsed.target_shift_type),
      requested_action: action(parsed.requested_action),
      reason: (parsed.reason as string) ?? "",
      partner_employee_first_name: (parsed.partner_employee_first_name as string) ?? "",
      partner_employee_last_name: (parsed.partner_employee_last_name as string) ?? "",
      partner_shift_date: (parsed.partner_shift_date as string) ?? "",
      partner_shift_type: shiftType(parsed.partner_shift_type),
    });
  }

  async function parseFromText(text: string) {
    setPreviewError("");
    setPreviewResult(null);
    if (!text.trim()) return;
    try {
      const result = await previewUnified({ text: text.trim() });
      setFormFromParsed(result.parsed);
      setPreviewResult({
        parsed: result.parsed,
        validation: {
          valid: result.validation.valid,
          errorCodes: result.validation.errorCodes,
          reason: result.validation.reason,
        },
        summary: result.summary,
        needsInput: result.needsInput,
      });
    } catch (err) {
      setPreviewError(err instanceof Error ? err.message : "Parse failed");
    }
  }

  async function onSubmitStructured(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setPreviewError("");
    try {
      await submitStructured(form);
      await load();
    } catch (err) {
      setPreviewError(err instanceof Error ? err.message : "Submit failed");
    } finally {
      setSubmitting(false);
    }
  }

  return {
    dates,
    shifts,
    loading,
    error,
    load,
    form,
    setForm,
    setFormFromParsed,
    previewResult,
    previewError,
    submitting,
    setTargetFromCell,
    shiftsFor,
    onPreview,
    onSubmitStructured,
    parseFromText,
    shiftTypes: SHIFT_TYPES,
  };
}
