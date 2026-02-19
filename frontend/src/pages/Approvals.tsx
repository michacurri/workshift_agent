import useApprovalsHook from "../hooks/approvals.hook";

export default function Approvals() {
  const { items, loading, load, error, act } = useApprovalsHook();

  return (
    <section>
      <h2>Pending Approvals</h2>
      <button type="button" onClick={load} disabled={loading}>
        Refresh
      </button>
      {error && <p style={{ color: "crimson" }}>{error}</p>}
      <ul style={{ listStyle: "none", padding: 0, marginTop: 16 }}>
        {items?.map((item) => {
          const summary =
            item.result_summary ||
            (item.requester_full_name && item.requested_action === "swap" && item.partner_full_name
              ? `${item.requester_full_name} ↔ ${item.partner_full_name}`
              : item.requester_full_name || item.requestId);

          return (
            <li
              key={item.requestId}
              style={{
                marginBottom: 16,
                padding: 12,
                border: `1px solid ${item.urgent ? "#c00" : "#ddd"}`,
                borderRadius: 4,
                backgroundColor: item.urgent ? "#fff0f0" : undefined,
              }}
            >
              {item.urgent && (
                <span style={{ fontSize: 12, color: "#c00", fontWeight: 600, marginRight: 8 }}>
                  &lt;48h
                </span>
              )}
              <div style={{ marginBottom: 8 }}>
                <strong>{summary}</strong>
              </div>
              <div style={{ fontSize: 12, color: "#555", marginBottom: 8 }}>
                <div>
                  <strong>Request ID:</strong> <code>{item.requestId}</code>
                </div>
                {item.submittedAt && (
                  <div>
                    <strong>Submitted:</strong>{" "}
                    {new Date(item.submittedAt).toLocaleString()}
                  </div>
                )}
                {item.requested_action && (
                  <div>
                    <strong>Action:</strong> {item.requested_action}
                  </div>
                )}
                {item.requester_full_name && (
                  <div>
                    <strong>Requester:</strong> {item.requester_full_name}
                    {item.requester_shift_date && item.requester_shift_type && (
                      <>
                        {" "}
                        – {item.requester_shift_date} ({item.requester_shift_type})
                      </>
                    )}
                  </div>
                )}
                {item.partner_full_name && (
                  <div>
                    <strong>Partner:</strong> {item.partner_full_name}
                    {item.partner_shift_date && item.partner_shift_type && (
                      <>
                        {" "}
                        – {item.partner_shift_date} ({item.partner_shift_type})
                      </>
                    )}
                  </div>
                )}
              </div>
              <div style={{ display: "flex", gap: 8, marginBottom: 8 }}>
                <button
                  type="button"
                  onClick={() => act(item.requestId, "approve")}
                >
                  Approve
                </button>
                <button
                  type="button"
                  onClick={() => act(item.requestId, "reject")}
                >
                  Reject
                </button>
              </div>
              <details>
                <summary style={{ cursor: "pointer" }}>View raw payload</summary>
                <pre style={{ marginTop: 8 }}>
                  {JSON.stringify(item.parsed, null, 2)}
                </pre>
              </details>
            </li>
          );
        })}
      </ul>
      {!items.length && !loading && <p>No pending approvals.</p>}
    </section>
  );
}
