import { useEffect, useState } from "react";
import { useAuth } from "../auth";
import { assignShift, getScheduleRequests, getShiftCandidates } from "../api";
import type { ScheduleRequestListItem, ShiftCandidateOut } from "../types";

export default function MyRequests() {
  const { currentUser } = useAuth();
  const isAdmin = currentUser?.role === "admin";
  const [items, setItems] = useState<ScheduleRequestListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [fillingShiftId, setFillingShiftId] = useState<string | null>(null);
  const [candidates, setCandidates] = useState<ShiftCandidateOut[]>([]);
  const [assigning, setAssigning] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError("");
    try {
      const list = await getScheduleRequests();
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

  async function openFill(shiftId: string) {
    setFillingShiftId(shiftId);
    setCandidates([]);
    try {
      const list = await getShiftCandidates(shiftId);
      setCandidates(list);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load candidates");
    }
  }

  function closeFill() {
    setFillingShiftId(null);
    setCandidates([]);
  }

  async function handleAssign(shiftId: string, employeeId: string) {
    setAssigning(employeeId);
    try {
      await assignShift(shiftId, employeeId);
      closeFill();
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Assign failed");
    } finally {
      setAssigning(null);
    }
  }

  if (loading) return <p>Loading requests…</p>;
  if (error) return <p style={{ color: "crimson" }}>{error}</p>;

  return (
    <section>
      <h2>My Requests</h2>
      <button type="button" onClick={load} disabled={loading}>
        Refresh
      </button>
      <ul style={{ listStyle: "none", padding: 0, marginTop: 16 }}>
        {items.map((item) => (
          <li
            key={item.requestId}
            style={{
              marginBottom: 12,
              padding: 12,
              border: `1px solid ${item.urgent ? "#c00" : "#ddd"}`,
              borderRadius: 8,
              backgroundColor: item.urgent ? "#fff0f0" : undefined,
            }}
          >
            {item.urgent && (
              <span style={{ fontSize: 12, color: "#c00", fontWeight: 600, marginRight: 8 }}>
                &lt;48h
              </span>
            )}
            <div style={{ fontWeight: 600, marginBottom: 4 }}>
              {item.summary ?? item.requestId}
            </div>
            <div style={{ fontSize: 14, color: "#555" }}>
              <span style={{ marginRight: 12 }}>Status: {item.status}</span>
              {item.requester_full_name && (
                <span style={{ marginRight: 12 }}>Requester: {item.requester_full_name}</span>
              )}
              <span>{new Date(item.created_at).toLocaleString()}</span>
            </div>
            {isAdmin && item.status === "pending_fill" && item.coverage_shift_id && (
              <div style={{ marginTop: 8 }}>
                {fillingShiftId !== item.coverage_shift_id ? (
                  <button type="button" onClick={() => openFill(item.coverage_shift_id!)}>
                    Fill coverage
                  </button>
                ) : (
                  <div style={{ marginTop: 8, padding: 8, border: "1px solid #eee", borderRadius: 4 }}>
                    <strong>Candidates</strong>
                    {candidates.length === 0 ? (
                      <p>No eligible candidates.</p>
                    ) : (
                      <ul style={{ listStyle: "none", padding: 0 }}>
                        {candidates.map((c) => (
                          <li key={c.employee_id} style={{ marginBottom: 8 }}>
                            {c.full_name} — {c.reason} (shifts this week: {c.shifts_this_week})
                            <button
                              type="button"
                              style={{ marginLeft: 8 }}
                              onClick={() => handleAssign(item.coverage_shift_id!, c.employee_id)}
                              disabled={assigning !== null}
                            >
                              {assigning === c.employee_id ? "…" : "Assign"}
                            </button>
                          </li>
                        ))}
                      </ul>
                    )}
                    <button type="button" onClick={closeFill} style={{ marginTop: 8 }}>
                      Cancel
                    </button>
                  </div>
                )}
              </div>
            )}
          </li>
        ))}
      </ul>
      {items.length === 0 && <p>No requests.</p>}
    </section>
  );
}
