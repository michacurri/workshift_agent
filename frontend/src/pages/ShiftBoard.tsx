import { useRef } from "react";
import { useAuth } from "../auth";
import useShiftBoardHook from "../hooks/shiftBoard.hook";
import type { StructuredRequestIn } from "../types";

export default function ShiftBoard() {
  const { currentUser } = useAuth();
  const pasteRef = useRef<HTMLTextAreaElement>(null);
  const {
    dates,
    loading,
    error,
    form,
    setForm,
    setTargetFromCell,
    previewResult,
    previewError,
    submitting,
    shiftsFor,
    onPreview,
    onSubmitStructured,
    parseFromText,
    shiftTypes,
  } = useShiftBoardHook();

  function handleParsePaste() {
    const text = pasteRef.current?.value?.trim();
    if (text) parseFromText(text);
  }

  function setCoverageFromShift(dateStr: string, type: "morning" | "night") {
    setForm((prev) => ({
      ...prev,
      requested_action: "cover",
      current_shift_date: dateStr,
      current_shift_type: type,
      employee_first_name: currentUser?.first_name ?? prev.employee_first_name,
      employee_last_name: currentUser?.last_name ?? prev.employee_last_name,
    }));
  }

  return (
    <section>
      <h2>Shift Board</h2>
      {error && <p style={{ color: "crimson" }}>{error}</p>}
      <div style={{ overflowX: "auto", marginBottom: 24 }}>
        <table style={{ borderCollapse: "collapse", minWidth: 600 }}>
          <thead>
            <tr>
              <th style={{ border: "1px solid #ddd", padding: 8 }}>Date</th>
              {shiftTypes.map((t) => (
                <th key={t} style={{ border: "1px solid #ddd", padding: 8, textTransform: "capitalize" }}>
                  {t}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {dates.map((d) => (
              <tr key={d}>
                <td style={{ border: "1px solid #ddd", padding: 8 }}>{d}</td>
                {shiftTypes.map((t) => {
                  const cellShifts = shiftsFor(d, t);
                  const isMyShift = currentUser && cellShifts.some((s) => s.assigned_employee_id === currentUser.id);
                  return (
                    <td
                      key={t}
                      style={{
                        border: "1px solid #ddd",
                        padding: 8,
                        cursor: "pointer",
                        verticalAlign: "top",
                        backgroundColor: isMyShift ? "#f0f9ff" : undefined,
                      }}
                      onClick={() => (isMyShift ? setCoverageFromShift(d, t) : setTargetFromCell(d, t))}
                      title={isMyShift ? "Request coverage for this shift" : "Select as target"}
                    >
                      {cellShifts.length === 0 && <span style={{ color: "#999" }}>Open</span>}
                      {cellShifts.map((s) => (
                        <div key={s.id}>
                          {s.assigned_employee_full_name || "(unassigned)"}
                        </div>
                      ))}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div style={{ marginBottom: 24 }}>
        <h3>Describe your request (or paste a message)</h3>
        <p style={{ fontSize: 14, color: "#555" }}>
          Type or paste a message like &quot;I need coverage for my night shift on 2025-02-20&quot; or
          &quot;Swap my Feb 22 morning with Alex&apos;s Feb 23 night&quot;, then click Preview.
        </p>
        <textarea
          ref={pasteRef}
          rows={3}
          placeholder="e.g. I need someone to cover my night shift on 2025-02-20"
          style={{ width: "100%", maxWidth: 650, display: "block", marginBottom: 8 }}
        />
        <button type="button" disabled={loading} onClick={handleParsePaste}>
          Preview
        </button>
      </div>

      <details style={{ marginBottom: 24 }}>
        <summary style={{ cursor: "pointer", fontWeight: 600 }}>Review details (optional)</summary>
        <form onSubmit={onPreview} style={{ marginTop: 12 }}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 12 }}>
          <div>
            <label>
              Requester first name
              <input
                type="text"
                value={form.employee_first_name}
                onChange={(e) => setForm({ ...form, employee_first_name: e.target.value })}
              />
            </label>
          </div>
          <div>
            <label>
              Requester last name
              <input
                type="text"
                value={form.employee_last_name || ""}
                onChange={(e) => setForm({ ...form, employee_last_name: e.target.value })}
              />
            </label>
          </div>
          <div>
            <label>
              Action
              <select
                value={form.requested_action || "move"}
                onChange={(e) =>
                  setForm({
                    ...form,
                    requested_action: e.target.value as StructuredRequestIn["requested_action"],
                  })
                }
              >
                <option value="move">Move</option>
                <option value="swap">Swap</option>
                <option value="cover">Cover</option>
              </select>
            </label>
          </div>
          <div>
            <label>
              Current shift date
              <input
                type="date"
                value={form.current_shift_date || ""}
                onChange={(e) => setForm({ ...form, current_shift_date: e.target.value })}
              />
            </label>
          </div>
          <div>
            <label>
              Current shift type
              <select
                value={form.current_shift_type || "morning"}
                onChange={(e) =>
                  setForm({
                    ...form,
                    current_shift_type: e.target.value as StructuredRequestIn["current_shift_type"],
                  })
                }
              >
                <option value="morning">Morning</option>
                <option value="night">Night</option>
              </select>
            </label>
          </div>
          <div>
            <label>
              Target date
              <input
                type="date"
                value={form.target_date || ""}
                onChange={(e) => setForm({ ...form, target_date: e.target.value })}
              />
            </label>
          </div>
          <div>
            <label>
              Target shift type
              <select
                value={form.target_shift_type || "morning"}
                onChange={(e) =>
                  setForm({
                    ...form,
                    target_shift_type: e.target.value as StructuredRequestIn["target_shift_type"],
                  })
                }
              >
                <option value="morning">Morning</option>
                <option value="night">Night</option>
              </select>
            </label>
          </div>
          <div>
            <label>
              Partner first name (for swap)
              <input
                type="text"
                value={form.partner_employee_first_name || ""}
                onChange={(e) => setForm({ ...form, partner_employee_first_name: e.target.value })}
              />
            </label>
          </div>
          <div>
            <label>
              Partner last name (for swap)
              <input
                type="text"
                value={form.partner_employee_last_name || ""}
                onChange={(e) => setForm({ ...form, partner_employee_last_name: e.target.value })}
              />
            </label>
          </div>
          <div>
            <label>
              Reason
              <input
                type="text"
                value={form.reason || ""}
                onChange={(e) => setForm({ ...form, reason: e.target.value })}
              />
            </label>
          </div>
        </div>
        {previewError && <p style={{ color: "crimson" }}>{previewError}</p>}
        <div style={{ marginTop: 12, display: "flex", gap: 8 }}>
          <button type="submit">Preview</button>
          <button type="button" onClick={onSubmitStructured} disabled={submitting}>
            {submitting ? "Submitting..." : "Submit for approval"}
          </button>
        </div>
        </form>
      </details>

      {previewResult && (
        <div style={{ marginTop: 16, padding: 16, border: "1px solid #ddd", borderRadius: 8 }}>
          <h3>Preview</h3>
          {previewResult.summary && (
            <p style={{ fontSize: 16, fontWeight: 600, marginBottom: 12 }}>{previewResult.summary}</p>
          )}
          {previewResult.needsInput && previewResult.needsInput.length > 0 && (
            <div style={{ marginBottom: 12, padding: 12, border: "1px solid #ffe1a6", background: "#fff7e6", borderRadius: 8 }}>
              <div style={{ fontWeight: 600, marginBottom: 6 }}>One more detail needed</div>
              <ul style={{ margin: 0, paddingLeft: 18 }}>
                {previewResult.needsInput.map((n) => (
                  <li key={n.field}>
                    {n.prompt}
                    {n.options && n.options.length > 0 ? ` (${n.options.join(" / ")})` : ""}
                  </li>
                ))}
              </ul>
            </div>
          )}
          <p>
            <strong>Valid:</strong> {previewResult.validation.valid ? "Yes" : "No"}
          </p>
          {!previewResult.validation.valid && (
            <>
              <p>
                <strong>Error codes:</strong> {previewResult.validation.errorCodes.join(", ")}
              </p>
              {previewResult.validation.reason && (
                <p>
                  <strong>Reason:</strong> {previewResult.validation.reason}
                </p>
              )}
            </>
          )}
          <details style={{ marginTop: 8 }}>
            <summary style={{ cursor: "pointer" }}>View parsed payload</summary>
            <pre style={{ marginTop: 8 }}>{JSON.stringify(previewResult.parsed, null, 2)}</pre>
          </details>
        </div>
      )}
    </section>
  );
}
