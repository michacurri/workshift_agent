import { act, renderHook, waitFor } from "@testing-library/react";
import { getShifts, previewStructured, previewUnified, submitStructured } from "../api";
import useShiftBoardHook from "./shiftBoard.hook";

vi.mock("../api", () => ({
  getShifts: vi.fn(),
  previewStructured: vi.fn(),
  previewUnified: vi.fn(),
  submitStructured: vi.fn(),
}));

describe("When shift-board workflows run through the hook", () => {
  it("And text parsing succeeds Then parsed fields hydrate the structured form", async () => {
    vi.mocked(getShifts).mockResolvedValue({ shifts: [] });
    vi.mocked(previewUnified).mockResolvedValue({
      parsed: {
        employee_first_name: "Priya",
        employee_last_name: "Smith",
        current_shift_date: "2026-02-21",
        current_shift_type: "night",
        target_date: "2026-02-22",
        target_shift_type: "morning",
        requested_action: "move",
      },
      validation: { valid: true, errorCodes: [], suggestions: [], validationDetails: {} },
      summary: "Looks good",
      needsInput: [],
    });

    const { result } = renderHook(() => useShiftBoardHook());
    await waitFor(() => expect(result.current.loading).toBe(false));
    await act(async () => {
      await result.current.parseFromText("move my shift to tomorrow morning");
    });

    expect(result.current.form.employee_first_name).toBe("Priya");
    expect(result.current.form.current_shift_type).toBe("night");
    expect(result.current.previewResult?.summary).toBe("Looks good");
  });

  it("And preview then submit succeed Then state transitions complete and shifts reload", async () => {
    const shiftsMock = vi.mocked(getShifts);
    shiftsMock.mockResolvedValue({ shifts: [] });
    vi.mocked(previewStructured).mockResolvedValue({
      parsed: { employee_first_name: "Priya" },
      validation: { valid: true, errorCodes: [], suggestions: [], validationDetails: {} },
      summary: "Preview summary",
      needsInput: [],
    });
    vi.mocked(submitStructured).mockResolvedValue({
      requestId: "req-1",
      status: "pending_admin",
      validation: { valid: true, errorCodes: [], suggestions: [], validationDetails: {} },
      correlationId: "corr-1",
    });

    const { result } = renderHook(() => useShiftBoardHook());
    await waitFor(() => expect(result.current.loading).toBe(false));
    act(() => {
      result.current.setForm((prev) => ({ ...prev, employee_first_name: "Priya" }));
    });

    await act(async () => {
      await result.current.onPreview({ preventDefault: vi.fn() } as unknown as React.FormEvent);
    });
    expect(result.current.previewResult?.summary).toBe("Preview summary");

    await act(async () => {
      await result.current.onSubmitStructured({ preventDefault: vi.fn() } as unknown as React.FormEvent);
    });
    expect(vi.mocked(submitStructured)).toHaveBeenCalledTimes(1);
    expect(shiftsMock.mock.calls.length).toBeGreaterThanOrEqual(2);
  });

  it("And the clock is fixed Then generated date windows remain deterministic", async () => {
    vi.setSystemTime(new Date("2026-02-20T20:00:00.000Z"));
    vi.mocked(getShifts).mockResolvedValue({ shifts: [] });

    const firstRun = renderHook(() => useShiftBoardHook());
    await waitFor(() => expect(firstRun.result.current.loading).toBe(false));
    const firstDates = [...firstRun.result.current.dates];
    firstRun.unmount();

    const secondRun = renderHook(() => useShiftBoardHook());
    await waitFor(() => expect(secondRun.result.current.loading).toBe(false));
    const secondDates = [...secondRun.result.current.dates];

    expect(firstDates).toHaveLength(7);
    expect(secondDates).toEqual(firstDates);
  });
});
