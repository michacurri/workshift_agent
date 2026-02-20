import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { assignShift, getScheduleRequests, getShiftCandidates } from "../api";
import MyRequests from "./MyRequests";

vi.mock("../api", () => ({
  assignShift: vi.fn(),
  getScheduleRequests: vi.fn(),
  getShiftCandidates: vi.fn(),
}));

vi.mock("../auth", () => ({
  useAuth: () => ({
    currentUser: {
      id: "admin-1",
      full_name: "Priya Smith",
      first_name: "Priya",
      last_name: "Smith",
      role: "admin",
    },
  }),
}));

describe("When an admin fills a pending coverage request", () => {
  it("And they choose an eligible candidate Then assignment is submitted and the list refreshes", async () => {
    vi.mocked(getScheduleRequests)
      .mockResolvedValueOnce([
        {
          requestId: "req-1",
          status: "pending_fill",
          summary: "Coverage needed",
          created_at: "2026-02-20T00:00:00Z",
          requester_full_name: "Alex Doe",
          coverage_shift_id: "shift-1",
          urgent: false,
        },
      ])
      .mockResolvedValueOnce([]);
    vi.mocked(getShiftCandidates).mockResolvedValue([
      {
        employee_id: "emp-2",
        full_name: "Jamie Doe",
        reason: "Eligible",
        shifts_this_week: 2,
      },
    ]);
    vi.mocked(assignShift).mockResolvedValue({
      shiftId: "shift-1",
      assignedEmployeeId: "emp-2",
    });
    const user = userEvent.setup();

    render(<MyRequests />);
    await waitFor(() => expect(screen.getByRole("button", { name: "Fill coverage" })).toBeInTheDocument());

    await user.click(screen.getByRole("button", { name: "Fill coverage" }));
    await waitFor(() => expect(screen.getByText(/Jamie Doe/i)).toBeInTheDocument());
    await user.click(screen.getByRole("button", { name: "Assign" }));

    await waitFor(() => expect(assignShift).toHaveBeenCalledWith("shift-1", "emp-2"));
    expect(getScheduleRequests).toHaveBeenCalledTimes(2);
  });
});
