import { useEffect, useState } from "react";
import { createEmployee, deleteEmployee, getEmployees, updateEmployee } from "../api";
import type { EmployeeOut } from "../types";

export default function AdminEmployees() {
  const [employees, setEmployees] = useState<EmployeeOut[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [role, setRole] = useState<"employee" | "admin">("employee");

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

  useEffect(() => {
    load();
  }, []);

  async function onCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!firstName.trim() || !lastName.trim()) return;
    try {
      await createEmployee({
        first_name: firstName.trim(),
        last_name: lastName.trim(),
        role,
        certifications: {},
        skills: {},
        availability: {},
      });
      setFirstName("");
      setLastName("");
      setRole("employee");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create employee");
    }
  }

  async function onToggleRole(emp: EmployeeOut) {
    try {
      await updateEmployee(emp.id, { role: emp.role === "admin" ? "employee" : "admin" });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update employee");
    }
  }

  async function onDelete(emp: EmployeeOut) {
    if (!window.confirm(`Delete ${emp.full_name}?`)) return;
    try {
      await deleteEmployee(emp.id);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete employee");
    }
  }

  return (
    <section>
      <h2>Admin: Employees</h2>
      {error && <p style={{ color: "crimson" }}>{error}</p>}
      <form onSubmit={onCreate} style={{ marginBottom: 16, display: "flex", gap: 8 }}>
        <input
          type="text"
          placeholder="First name"
          value={firstName}
          onChange={(e) => setFirstName(e.target.value)}
        />
        <input
          type="text"
          placeholder="Last name"
          value={lastName}
          onChange={(e) => setLastName(e.target.value)}
        />
        <select value={role} onChange={(e) => setRole(e.target.value as "employee" | "admin")}>
          <option value="employee">Employee</option>
          <option value="admin">Admin</option>
        </select>
        <button type="submit">Create</button>
      </form>
      {loading && <p>Loading...</p>}
      <ul style={{ listStyle: "none", padding: 0 }}>
        {employees.map((emp) => (
          <li
            key={emp.id}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              marginBottom: 8,
              border: "1px solid #ddd",
              borderRadius: 4,
              padding: 8,
            }}
          >
            <div style={{ flex: 1 }}>
              <strong>{emp.full_name}</strong>{" "}
              <span style={{ fontSize: 12, color: "#555" }}>({emp.role})</span>
            </div>
            <button type="button" onClick={() => onToggleRole(emp)}>
              Set {emp.role === "admin" ? "Employee" : "Admin"}
            </button>
            <button type="button" onClick={() => onDelete(emp)}>
              Delete
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}

