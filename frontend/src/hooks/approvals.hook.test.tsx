import { act, renderHook, waitFor } from "@testing-library/react";
import { approveRequest, getPendingApprovals, rejectRequest } from "../api";
import useApprovalsHook from "./approvals.hook";

vi.mock("../api", () => ({
  getPendingApprovals: vi.fn(),
  approveRequest: vi.fn(),
  rejectRequest: vi.fn(),
}));

describe("When an admin manages approvals", () => {
  it("And pending items exist Then the hook loads and exposes them", async () => {
    const pendingMock = vi.mocked(getPendingApprovals);
    pendingMock.mockResolvedValue([
      {
        requestId: "req-1",
        submittedAt: "2026-02-20T00:00:00Z",
        parsed: {},
      },
    ]);

    const { result } = renderHook(() => useApprovalsHook());
    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.items).toHaveLength(1);
    expect(result.current.items[0]?.requestId).toBe("req-1");
  });

  it("And loading fails Then the hook exposes an error message", async () => {
    vi.mocked(getPendingApprovals).mockRejectedValue(new Error("load failed"));

    const { result } = renderHook(() => useApprovalsHook());
    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.error).toBe("load failed");
  });

  it("And an approve/reject action succeeds Then list data is refreshed", async () => {
    const pendingMock = vi.mocked(getPendingApprovals);
    const approveMock = vi.mocked(approveRequest);
    const rejectMock = vi.mocked(rejectRequest);

    pendingMock
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce([
        {
          requestId: "req-2",
          submittedAt: "2026-02-20T00:00:00Z",
          parsed: {},
        },
      ])
      .mockResolvedValueOnce([]);
    approveMock.mockResolvedValue({ requestId: "req-2", status: "approved", correlationId: "c1" });
    rejectMock.mockResolvedValue({ requestId: "req-3", status: "rejected", correlationId: "c2" });

    const { result } = renderHook(() => useApprovalsHook());
    await waitFor(() => expect(result.current.loading).toBe(false));

    await act(async () => {
      await result.current.act("req-2", "approve");
    });
    expect(approveMock).toHaveBeenCalledWith("req-2");
    expect(result.current.items[0]?.requestId).toBe("req-2");

    await act(async () => {
      await result.current.act("req-3", "reject");
    });
    expect(rejectMock).toHaveBeenCalledWith("req-3");
    expect(pendingMock).toHaveBeenCalledTimes(3);
  });
});
