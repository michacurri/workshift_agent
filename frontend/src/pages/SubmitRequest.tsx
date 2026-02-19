import useRequestHook from "../hooks/request.hook";

export default function SubmitRequest() {
  const { text, loading, result, error, onSubmit, setText } = useRequestHook();

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
      {result && (
        <div>
          <h3>Result</h3>
          <pre>{JSON.stringify(result, null, 2)}</pre>
        </div>
      )}
    </section>
  );
}
