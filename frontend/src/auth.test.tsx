import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderHook } from "@testing-library/react";
import { AuthProvider, useAuth, type CurrentUser } from "./auth";

function Probe() {
  const { currentUser, setCurrentUser, logout } = useAuth();
  const nextUser: CurrentUser = {
    id: "emp-1",
    full_name: "Priya Smith",
    first_name: "Priya",
    last_name: "Smith",
    role: "admin",
  };

  return (
    <div>
      <p data-testid="name">{currentUser?.full_name ?? "none"}</p>
      <button type="button" onClick={() => setCurrentUser(nextUser)}>
        login
      </button>
      <button type="button" onClick={logout}>
        logout
      </button>
    </div>
  );
}

describe("When auth context manages employee identity", () => {
  it("And a saved user exists Then state hydrates from localStorage", async () => {
    window.localStorage.setItem(
      "currentUser",
      JSON.stringify({
        id: "emp-2",
        full_name: "Alex Doe",
        first_name: "Alex",
        last_name: "Doe",
        role: "employee",
      })
    );

    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId("name")).toHaveTextContent("Alex Doe");
    });
  });

  it("And an employee logs in then logs out Then storage persists and clears correctly", async () => {
    const user = userEvent.setup();
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>
    );

    await user.click(screen.getByRole("button", { name: "login" }));
    const persisted = window.localStorage.getItem("currentUser");
    expect(persisted).toBeTruthy();
    expect(persisted).toContain("Priya Smith");

    await user.click(screen.getByRole("button", { name: "logout" }));
    expect(window.localStorage.getItem("currentUser")).toBeNull();
    expect(screen.getByTestId("name")).toHaveTextContent("none");
  });

  it("And useAuth is called outside a provider Then it throws a guard error", () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    expect(() => renderHook(() => useAuth())).toThrow("useAuth must be used within AuthProvider");
  });
});
