import useMetricsHook from "../hooks/metrics.hook";

export default function Dashboard() {
  const { metrics, load, error } = useMetricsHook();

  return (
    <section>
      <h2>Dashboard</h2>
      <button type="button" onClick={load}>
        Refresh
      </button>
      {error && <p style={{ color: "crimson" }}>{error}</p>}
      {metrics ? (
        <pre>{JSON.stringify(metrics, null, 2)}</pre>
      ) : (
        <p>Loading metrics...</p>
      )}
    </section>
  );
}
