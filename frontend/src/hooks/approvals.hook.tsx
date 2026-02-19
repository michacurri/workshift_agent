import { useState, useEffect } from "react";
import { getPendingApprovals, approveRequest, rejectRequest } from "../api";
import type { PendingApprovalItem } from "../types";

export default function useApprovalsHook() {
  const [items, setItems] = useState<PendingApprovalItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function load() {
    setLoading(true);
    setError("");
    try {
      setItems(await getPendingApprovals());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }

  async function act(id: string, action: "approve" | "reject") {
    try {
      if (action === "approve") await approveRequest(id);
      else await rejectRequest(id);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Action failed");
    }
  }

  useEffect(() => {
    load();
  }, []);

  return { items, loading, load, error, act };
}