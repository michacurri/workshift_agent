import { useState } from "react";
import { ScheduleRequestOut } from "../types";
import { submitRequest } from "../api";

export default function useRequestHook() {
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ScheduleRequestOut | null>(null);
  const [error, setError] = useState("");

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!text.trim()) return;
    setLoading(true);
    setError("");
    try {
      const data = await submitRequest(text);
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setLoading(false);
    }
  }

  return {
    text, loading, result, error, onSubmit, setText,
  }
}