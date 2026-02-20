import { render, screen } from "@testing-library/react";
import ShiftBoard from "./ShiftBoard";

vi.mock("../auth", () => ({
  useAuth: () => ({
    currentUser: {
      id: "emp-1",
      first_name: "Priya",
      last_name: "Smith",
      full_name: "Priya Smith",
      role: "employee",
    },
  }),
}));

vi.mock("../hooks/shiftBoard.hook", () => ({
  default: () => ({
    dates: ["2026-02-20"],
    shifts: [],
    loading: false,
    error: "",
    form: {
      employee_first_name: "",
      employee_last_name: "",
      current_shift_date: "",
      current_shift_type: "morning",
      target_date: "",
      target_shift_type: "morning",
      requested_action: "move",
      partner_employee_first_name: "",
      partner_employee_last_name: "",
      partner_shift_date: "",
      partner_shift_type: "morning",
      reason: "",
    },
    setForm: vi.fn(),
    setTargetFromCell: vi.fn(),
    previewResult: {
      parsed: {},
      validation: { valid: false, errorCodes: ["MISSING_DATE"] },
      summary: "Need one more detail",
      needsInput: [{ field: "target_date", prompt: "What date?" }],
    },
    previewError: "",
    submitting: false,
    shiftsFor: vi.fn(() => []),
    onPreview: vi.fn(),
    onSubmitStructured: vi.fn(),
    parseFromText: vi.fn(),
    shiftTypes: ["morning", "night"],
  }),
}));

describe("When an employee previews schedule changes in ShiftBoard", () => {
  it("And more fields are needed Then the UI surfaces needsInput guidance", () => {
    render(<ShiftBoard />);
    expect(screen.getByText("One more detail needed")).toBeInTheDocument();
    expect(screen.getByText("What date?")).toBeInTheDocument();
  });
});
