import { useState } from "react";
import type { PreviewResponse, ScheduleRequestOut } from "../types";
import { previewUnified, submitRequest } from "../api";

export default function useRequestHook() {
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ScheduleRequestOut | null>(null);
  const [preview, setPreview] = useState<PreviewResponse | null>(null);
  const [error, setError] = useState("");

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!text.trim()) return;
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const p = await previewUnified({ text: text.trim() });
      setPreview(p);
      if (!p.validation.valid || (p.needsInput && p.needsInput.length > 0)) {
        setError("More information is needed. Use Shift Board to review and complete the request.");
        return;
      }
      const data = await submitRequest(text.trim());
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setLoading(false);
    }
  }

  return {
    text,
    loading,
    result,
    preview,
    error,
    onSubmit,
    setText,
  };
}