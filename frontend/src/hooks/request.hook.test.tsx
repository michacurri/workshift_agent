import { act, renderHook } from "@testing-library/react";
import { previewUnified, submitRequest } from "../api";
import useRequestHook from "./request.hook";

vi.mock("../api", () => ({
  previewUnified: vi.fn(),
  submitRequest: vi.fn(),
}));

describe("When an employee submits a natural-language request", () => {
  it("And the request text is empty Then preview and submit are not called", async () => {
    const previewMock = vi.mocked(previewUnified);
    const submitMock = vi.mocked(submitRequest);
    const { result } = renderHook(() => useRequestHook());

    await act(async () => {
      await result.current.onSubmit({ preventDefault: vi.fn() } as unknown as React.FormEvent<HTMLFormElement>);
    });

    expect(previewMock).not.toHaveBeenCalled();
    expect(submitMock).not.toHaveBeenCalled();
  });

  it("And preview needs more input Then submission is blocked with guidance", async () => {
    const previewMock = vi.mocked(previewUnified);
    const submitMock = vi.mocked(submitRequest);
    previewMock.mockResolvedValue({
      parsed: {},
      validation: { valid: true, errorCodes: [], suggestions: [], validationDetails: {} },
      summary: "Need more",
      needsInput: [{ field: "target_date", prompt: "What date?" }],
    });
    const { result } = renderHook(() => useRequestHook());

    act(() => {
      result.current.setText("Need coverage tomorrow");
    });
    await act(async () => {
      await result.current.onSubmit({ preventDefault: vi.fn() } as unknown as React.FormEvent<HTMLFormElement>);
    });

    expect(previewMock).toHaveBeenCalledTimes(1);
    expect(submitMock).not.toHaveBeenCalled();
    expect(result.current.error).toContain("More information is needed");
  });

  it("And preview is valid Then the request submits and result is stored", async () => {
    const previewMock = vi.mocked(previewUnified);
    const submitMock = vi.mocked(submitRequest);
    previewMock.mockResolvedValue({
      parsed: {},
      validation: { valid: true, errorCodes: [], suggestions: [], validationDetails: {} },
      summary: "Valid",
      needsInput: [],
    });
    submitMock.mockResolvedValue({
      requestId: "req-1",
      status: "pending_admin",
      validation: { valid: true, errorCodes: [], suggestions: [], validationDetails: {} },
      correlationId: "corr-1",
      summary: "Submitted",
    });
    const { result } = renderHook(() => useRequestHook());

    act(() => {
      result.current.setText("Swap my shift with Alex");
    });
    await act(async () => {
      await result.current.onSubmit({ preventDefault: vi.fn() } as unknown as React.FormEvent<HTMLFormElement>);
    });

    expect(previewMock).toHaveBeenCalledTimes(1);
    expect(submitMock).toHaveBeenCalledTimes(1);
    expect(result.current.result?.requestId).toBe("req-1");
    expect(result.current.error).toBe("");
  });
});
