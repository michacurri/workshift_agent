import { useState } from "react";
import Approvals from "./pages/Approvals";
import Consents from "./pages/Consents";
import Dashboard from "./pages/Dashboard";
import MyRequests from "./pages/MyRequests";
import SubmitRequest from "./pages/SubmitRequest";
import ShiftBoard from "./pages/ShiftBoard";
import Login from "./pages/Login";
import AdminEmployees from "./pages/AdminEmployees";
import { useAuth } from "./auth";

type Tab = "request" | "approvals" | "consents" | "my-requests" | "dashboard" | "shiftboard" | "admin";

export default function App() {
  const [tab, setTab] = useState<Tab>("shiftboard");
  const { currentUser, logout } = useAuth();

  if (!currentUser) {
    return (
      <main style={{ maxWidth: 900, margin: "2rem auto", fontFamily: "sans-serif" }}>
        <h1>Shift Scheduler Agent</h1>
        <Login />
      </main>
    );
  }

  const isAdmin = currentUser.role === "admin";

  return (
    <main style={{ maxWidth: 900, margin: "2rem auto", fontFamily: "sans-serif" }}>
      <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h1>Shift Scheduler Agent</h1>
        <div style={{ fontSize: 14 }}>
          <span>
            Signed in as <strong>{currentUser.full_name}</strong> ({currentUser.role})
          </span>
          <button type="button" onClick={logout} style={{ marginLeft: 8 }}>
            Logout
          </button>
        </div>
      </header>
      <nav style={{ display: "flex", gap: 8, margin: "16px 0" }}>
        <button type="button" onClick={() => setTab("request")}>
          Request
        </button>
        {isAdmin && (
          <button type="button" onClick={() => setTab("approvals")}>
            Approvals
          </button>
        )}
        <button type="button" onClick={() => setTab("consents")}>
          Consents
        </button>
        <button type="button" onClick={() => setTab("my-requests")}>
          My Requests
        </button>
        {isAdmin && (
          <button type="button" onClick={() => setTab("dashboard")}>
            Dashboard
          </button>
        )}
        <button type="button" onClick={() => setTab("shiftboard")}>
          Shiftboard
        </button>
        {isAdmin && (
          <button type="button" onClick={() => setTab("admin")}>
            Admin
          </button>
        )}
      </nav>
      {tab === "request" && <SubmitRequest />}
      {tab === "approvals" && isAdmin && <Approvals />}
      {tab === "consents" && <Consents />}
      {tab === "my-requests" && <MyRequests />}
      {tab === "dashboard" && isAdmin && <Dashboard />}
      {tab === "shiftboard" && <ShiftBoard />}
      {tab === "admin" && isAdmin && <AdminEmployees />}
    </main>
  );
}
