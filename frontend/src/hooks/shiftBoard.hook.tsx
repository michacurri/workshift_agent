import { useEffect, useMemo, useState } from "react";
import { getShifts, previewStructured, previewUnified, submitStructured } from "../api";
import type { ShiftItem, StructuredRequestIn } from "../types";

const SHIFT_TYPES = ["morning", "night"] as const;
type ShiftType = (typeof SHIFT_TYPES)[number];

function toISODate(d: Date): string {
  return d.toISOString().slice(0, 10);
}

function getNextNDays(start: Date, days: number): string[] {
  const dates: string[] = [];
  for (let i = 0; i < days; i += 1) {
    const d = new Date(start);
    d.setDate(start.getDate() + i);
    dates.push(toISODate(d));
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
};

export default function useShiftBoardHook() {
  const today = useMemo(() => new Date(), []);
  const from = toISODate(today);
  const days = 7;
  const dates = useMemo(() => getNextNDays(new Date(from), days), [from, days]);

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
      });
    } catch (err) {
      setPreviewError(err instanceof Error ? err.message : "Preview failed");
    }
  }

  function setFormFromParsed(parsed: Record<string, unknown>) {
    setForm({
      employee_first_name: (parsed.employee_first_name as string) ?? "",
      employee_last_name: (parsed.employee_last_name as string) ?? "",
      current_shift_date: (parsed.current_shift_date as string) ?? "",
      current_shift_type: (parsed.current_shift_type as string) ?? "morning",
      target_date: (parsed.target_date as string) ?? "",
      target_shift_type: (parsed.target_shift_type as string) ?? "morning",
      requested_action: (parsed.requested_action as string) ?? "move",
      reason: (parsed.reason as string) ?? "",
      partner_employee_first_name: (parsed.partner_employee_first_name as string) ?? "",
      partner_employee_last_name: (parsed.partner_employee_last_name as string) ?? "",
      partner_shift_date: (parsed.partner_shift_date as string) ?? "",
      partner_shift_type: (parsed.partner_shift_type as string) ?? "morning",
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
