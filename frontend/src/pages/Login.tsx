import { useEffect, useState } from "react";
import { getEmployees } from "../api";
import type { EmployeeOut } from "../types";
import { useAuth } from "../auth";

export default function Login() {
  const { setCurrentUser } = useAuth();
  const [employees, setEmployees] = useState<EmployeeOut[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError("");
      try {
        const list = await getEmployees();
        setEmployees(list);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load employees");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  return (
    <section>
      <h2>Dev Login</h2>
      <p>Select an employee to act as the current user.</p>
      {error && <p style={{ color: "crimson" }}>{error}</p>}
      {loading && <p>Loading employees...</p>}
      <ul style={{ listStyle: "none", padding: 0, marginTop: 16 }}>
        {employees.map((emp) => (
          <li key={emp.id} style={{ marginBottom: 8 }}>
            <button
              type="button"
              onClick={() =>
                setCurrentUser({
                  id: emp.id,
                  full_name: emp.full_name,
                  role: emp.role === "admin" ? "admin" : "employee",
                })
              }
            >
              {emp.full_name}{" "}
              <span style={{ fontSize: 12, color: "#555" }}>
                ({emp.role})
              </span>
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}

