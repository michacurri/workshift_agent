import useRequestHook from "../hooks/request.hook";

export default function SubmitRequest() {
  const { text, loading, result, preview, error, onSubmit, setText } = useRequestHook();

  return (
    <section>
      <h2>Submit Request</h2>
      <form onSubmit={onSubmit}>
        <textarea
          rows={5}
          style={{ width: "100%" }}
          placeholder="Swap John from Tuesday night to Wednesday morning"
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
        <button disabled={loading} type="submit">
          {loading ? "Submitting..." : "Submit"}
        </button>
      </form>
      {error && <p style={{ color: "crimson" }}>{error}</p>}
      {preview && (
        <div style={{ marginTop: 12, padding: 12, border: "1px solid #ddd", borderRadius: 8 }}>
          <div style={{ fontWeight: 600, marginBottom: 6 }}>Preview</div>
          <div style={{ marginBottom: 8 }}>{preview.summary}</div>
          {preview.needsInput && preview.needsInput.length > 0 && (
            <div style={{ marginBottom: 8 }}>
              <div style={{ fontWeight: 600, marginBottom: 4 }}>Needs input</div>
              <ul style={{ margin: 0, paddingLeft: 18 }}>
                {preview.needsInput.map((n) => (
                  <li key={n.field}>
                    {n.prompt}
                    {n.options && n.options.length > 0 ? ` (${n.options.join(" / ")})` : ""}
                  </li>
                ))}
              </ul>
            </div>
          )}
          <details>
            <summary style={{ cursor: "pointer" }}>Parsed payload</summary>
            <pre style={{ marginTop: 8 }}>{JSON.stringify(preview.parsed, null, 2)}</pre>
          </details>
        </div>
      )}
      {result && (
        <div>
          <h3>Result</h3>
          <pre>{JSON.stringify(result, null, 2)}</pre>
        </div>
      )}
    </section>
  );
}
