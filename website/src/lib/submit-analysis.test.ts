import { describe, it, expect, vi } from "vitest";
import { submitAnalysis } from "./submit-analysis";
import type { SubmissionPayloadT } from "@/lib/schemas";

const PAYLOAD = {
  make: "Toyota",
  model: "Camry",
  trims: ["XSE"],
  colors: ["Ocean Gem"],
  zipcode: "90210",
  radius: "50",
  email: "test@example.com",
} as SubmissionPayloadT;

function jsonResponse(status: number, body: unknown): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response;
}

describe("submitAnalysis", () => {
  it("confirms when the server answers 2xx inside the window", async () => {
    const fetchImpl = vi.fn().mockResolvedValue(
      jsonResponse(200, { success: true, listingsFound: 8 })
    );

    const outcome = await submitAnalysis(PAYLOAD, { fetchImpl });

    expect(outcome).toEqual({ status: "confirmed" });
  });

  it("surfaces a spent invitation code with the server's own message", async () => {
    const fetchImpl = vi.fn().mockResolvedValue(
      jsonResponse(403, {
        error: {
          code: "INVITE_REQUIRED",
          message: "This invitation code has already been used.",
        },
      })
    );

    const outcome = await submitAnalysis(PAYLOAD, { fetchImpl });

    expect(outcome).toEqual({
      status: "error",
      code: "INVITE_REQUIRED",
      message: "This invitation code has already been used.",
    });
  });

  it("surfaces a validation error", async () => {
    const fetchImpl = vi.fn().mockResolvedValue(
      jsonResponse(400, {
        error: { code: "VALIDATION_ERROR", message: "Pick at least one trim" },
      })
    );

    const outcome = await submitAnalysis(PAYLOAD, { fetchImpl });

    expect(outcome).toMatchObject({
      status: "error",
      code: "VALIDATION_ERROR",
    });
  });

  it("accepts optimistically when no verdict arrives in time", async () => {
    // Never settles — stands in for the 10-30s analysis path.
    const fetchImpl = vi.fn().mockReturnValue(new Promise(() => {}));

    const outcome = await submitAnalysis(PAYLOAD, {
      fetchImpl,
      timeoutMs: 20,
    });

    expect(outcome).toEqual({ status: "accepted" });
  });

  it("never aborts the in-flight request when it stops waiting", async () => {
    // A signal would let the timeout cancel the analysis mid-flight, which is
    // exactly what this design must not do.
    const fetchImpl = vi.fn().mockReturnValue(new Promise(() => {}));

    await submitAnalysis(PAYLOAD, { fetchImpl, timeoutMs: 20 });

    const init = fetchImpl.mock.calls[0][1];
    expect(init.signal).toBeUndefined();
  });

  it("reports a network failure rather than a false confirmation", async () => {
    const fetchImpl = vi.fn().mockRejectedValue(new TypeError("Failed to fetch"));

    const outcome = await submitAnalysis(PAYLOAD, { fetchImpl });

    expect(outcome).toMatchObject({ status: "error", code: "NETWORK_ERROR" });
  });

  it("falls back to a generic message when the error body isn't our envelope", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: false,
      status: 502,
      json: async () => {
        throw new SyntaxError("Unexpected token < in JSON");
      },
    } as unknown as Response);

    const outcome = await submitAnalysis(PAYLOAD, { fetchImpl });

    expect(outcome.status).toBe("error");
    if (outcome.status === "error") {
      expect(outcome.code).toBe("UPSTREAM_ERROR");
      expect(outcome.message).toMatch(/something went wrong/i);
    }
  });

  it("posts the payload as JSON to /api/submit", async () => {
    const fetchImpl = vi.fn().mockResolvedValue(jsonResponse(200, {}));

    await submitAnalysis(PAYLOAD, { fetchImpl });

    const [url, init] = fetchImpl.mock.calls[0];
    expect(url).toBe("/api/submit");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body)).toEqual(PAYLOAD);
  });
});
