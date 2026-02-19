import { useEffect, useState } from "react";
import { getMetrics } from "../api";
import type { MetricsOut } from "../types";

export default function useMetricsHook() {
  const [metrics, setMetrics] = useState<MetricsOut | null>(null);
  const [error, setError] = useState("");

  async function load() {
    try {
      setMetrics(await getMetrics());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load metrics");
    }
  }

  useEffect(() => {
    load();
  }, []);

  return { metrics, load, error }
}