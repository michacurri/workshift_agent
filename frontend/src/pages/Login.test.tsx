import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { getEmployees } from "../api";
import { AuthProvider, useAuth } from "../auth";
import Login from "./Login";

vi.mock("../api", () => ({
  getEmployees: vi.fn(),
}));

function CurrentUserProbe() {
  const { currentUser } = useAuth();
  return <p data-testid="current-user">{currentUser?.full_name ?? "none"}</p>;
}

describe("When a user needs to log in as an employee", () => {
  it("And the roster loads Then selecting a user sets the current identity", async () => {
    vi.mocked(getEmployees).mockResolvedValue([
      {
        id: "emp-1",
        full_name: "Priya Smith",
        first_name: "Priya",
        last_name: "Smith",
        role: "admin",
        certifications: {},
        skills: {},
        availability: {},
      },
    ]);
    const user = userEvent.setup();

    render(
      <AuthProvider>
        <Login />
        <CurrentUserProbe />
      </AuthProvider>
    );

    await waitFor(() => expect(screen.getByRole("button", { name: /Priya Smith/i })).toBeInTheDocument());
    await user.click(screen.getByRole("button", { name: /Priya Smith/i }));

    expect(screen.getByTestId("current-user")).toHaveTextContent("Priya Smith");
  });
});
