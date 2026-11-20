import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@/lib/clients/agent-client", () => ({
  analyzeListings: vi.fn(),
}));
vi.mock("@/lib/logger", () => ({
  logger: { info: vi.fn(), warn: vi.fn(), error: vi.fn() },
}));

import { analyzeListings } from "@/lib/clients/agent-client";
import { submitCar } from "./submission-service";

const PAYLOAD = {
  make: "Toyota",
  model: "Camry",
  trims: ["XSE", "SE"],
  colors: ["Ice Cap", "Midnight Black Metallic"],
  zipcode: "90210",
  radius: "50",
  email: "test@example.com",
};

beforeEach(() => vi.clearAllMocks());

describe("submitCar", () => {
  it("returns listingsFound and dryRun from agent response", async () => {
    vi.mocked(analyzeListings).mockResolvedValue({
      success: true,
      dry_run: true,
      num_found: 8,
      results_id: "abc-123",
    });

    const result = await submitCar(PAYLOAD, "DALE-7K3M");

    expect(result.success).toBe(true);
    expect(result.listingsFound).toBe(8);
    expect(result.dryRun).toBe(true);
  });

  it("passes all preference fields to the agent", async () => {
    vi.mocked(analyzeListings).mockResolvedValue({ success: true, num_found: 0 });

    await submitCar(PAYLOAD, "DALE-7K3M");

    const call = vi.mocked(analyzeListings).mock.calls[0][0];
    expect(call.make).toBe("Toyota");
    expect(call.email).toBe("test@example.com");
    expect(call.radius).toBe("50");
  });

  it("forwards the invite code so the agent can spend it", async () => {
    vi.mocked(analyzeListings).mockResolvedValue({ success: true, num_found: 0 });

    await submitCar(PAYLOAD, "DALE-7K3M");

    expect(vi.mocked(analyzeListings).mock.calls[0][0].invite_code).toBe(
      "DALE-7K3M"
    );
  });

  it("defaults listingsFound to 0 when agent omits num_found", async () => {
    vi.mocked(analyzeListings).mockResolvedValue({ success: true });

    const result = await submitCar(PAYLOAD, "DALE-7K3M");

    expect(result.listingsFound).toBe(0);
  });
});
