import { getMetrics, previewStructured } from "./api";
import type { StructuredRequestIn } from "./types";

function okJson(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

function errorJson(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("When an employee uses frontend API helpers", () => {
  it("And optional structured fields are blank Then payload fields are normalized to null", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      okJson({
        parsed: {},
        validation: { valid: true, errorCodes: [], suggestions: [], validationDetails: {} },
        summary: "ok",
      })
    );

    const body: StructuredRequestIn = {
      employee_first_name: "Priya",
      employee_last_name: "",
      current_shift_date: "",
      current_shift_type: "morning",
      target_date: "",
      target_shift_type: "night",
      requested_action: "move",
      partner_employee_first_name: "",
      partner_employee_last_name: "",
      partner_shift_date: "",
      partner_shift_type: "morning",
      reason: "",
    };

    await previewStructured(body);
    const init = fetchSpy.mock.calls[0]?.[1];
    const serialized = (init?.body as string) ?? "{}";
    const payload = JSON.parse(serialized) as { structured: StructuredRequestIn };
    expect(payload.structured.employee_last_name).toBeNull();
    expect(payload.structured.current_shift_date).toBeNull();
    expect(payload.structured.target_date).toBeNull();
    expect(payload.structured.partner_shift_date).toBeNull();
    expect(payload.structured.partner_employee_first_name).toBeNull();
    expect(payload.structured.partner_employee_last_name).toBeNull();
    expect(payload.structured.reason).toBeNull();
  });

  it("And a current user exists Then requests include X-Employee-Id header", async () => {
    window.localStorage.setItem("currentUser", JSON.stringify({ id: "emp-123" }));
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      okJson({
        total_requests: 1,
        approval_rate: 1,
        average_processing_time: 1,
        parse_time_avg: 1,
        validation_time_avg: 1,
        approval_latency_avg: 1,
      })
    );

    await getMetrics();
    const init = fetchSpy.mock.calls[0]?.[1];
    const headers = (init?.headers ?? {}) as Record<string, string>;
    expect(headers["X-Employee-Id"]).toBe("emp-123");
  });

  it("And backend failures vary Then user-facing fallback messaging is stable", async () => {
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(errorJson(400, { userMessage: "user-friendly" }))
      .mockResolvedValueOnce(errorJson(500, { developerMessage: "developer-only" }))
      .mockResolvedValueOnce(errorJson(503, {}));

    await expect(getMetrics()).rejects.toThrow("user-friendly");
    await expect(getMetrics()).rejects.toThrow("developer-only");
    await expect(getMetrics()).rejects.toThrow("Request failed");
  });
});
