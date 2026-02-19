import { useEffect, useState } from "react";
import { getPartnerPending, partnerAccept, partnerReject } from "../api";
import type { PartnerPendingItem } from "../types";

export default function Consents() {
  const [items, setItems] = useState<PartnerPendingItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [acting, setActing] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError("");
    try {
      const list = await getPartnerPending();
      setItems(list);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleAccept(id: string) {
    setActing(id);
    try {
      await partnerAccept(id);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Accept failed");
    } finally {
      setActing(null);
    }
  }

  async function handleReject(id: string) {
    setActing(id);
    try {
      await partnerReject(id);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Reject failed");
    } finally {
      setActing(null);
    }
  }

  if (loading) return <p>Loading consent requests…</p>;
  if (error) return <p style={{ color: "crimson" }}>{error}</p>;

  return (
    <section>
      <h2>Swap consents</h2>
      <p style={{ fontSize: 14, color: "#555" }}>
        Requests where you are the swap partner. Accept to send to admin; reject to decline.
      </p>
      {items.length === 0 ? (
        <p>No pending consent requests.</p>
      ) : (
        <ul style={{ listStyle: "none", padding: 0 }}>
          {items.map((item) => (
            <li
              key={item.requestId}
              style={{
                border: "1px solid #ddd",
                borderRadius: 8,
                padding: 16,
                marginBottom: 12,
              }}
            >
              <p style={{ fontWeight: 600, marginBottom: 8 }}>{item.summary}</p>
              {item.requester_full_name && (
                <p style={{ fontSize: 14, color: "#555" }}>Requester: {item.requester_full_name}</p>
              )}
              {item.workload_shifts_this_week != null && (
                <p style={{ fontSize: 14, color: "#555" }}>
                  Your shifts this week: {item.workload_shifts_this_week}
                </p>
              )}
              <div style={{ marginTop: 12, display: "flex", gap: 8 }}>
                <button
                  type="button"
                  onClick={() => handleAccept(item.requestId)}
                  disabled={acting !== null}
                >
                  {acting === item.requestId ? "…" : "Accept"}
                </button>
                <button
                  type="button"
                  onClick={() => handleReject(item.requestId)}
                  disabled={acting !== null}
                >
                  Reject
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
