import { describe, it, expect } from "vitest";
import { SubmissionPayload } from "./submission";

const VALID = {
  make: "Toyota",
  model: "Camry",
  trims: ["SE", "XSE"],
  colors: ["Supersonic Red", "Ocean Gem"],
  zipcode: "90210",
  radius: "50",
  email: "test@example.com",
};

describe("SubmissionPayload catalog validation", () => {
  it("accepts a valid model/trim/color combination", () => {
    expect(SubmissionPayload.safeParse(VALID).success).toBe(true);
  });

  it("rejects non-Toyota makes", () => {
    const r = SubmissionPayload.safeParse({ ...VALID, make: "Honda" });
    expect(r.success).toBe(false);
    expect(r.error?.issues[0]?.message).toMatch(/Unsupported make/);
  });

  it("rejects unknown models", () => {
    const r = SubmissionPayload.safeParse({ ...VALID, model: "Celica" });
    expect(r.success).toBe(false);
    expect(r.error?.issues[0]?.message).toMatch(/Unknown Toyota model/);
  });

  it("rejects trims that exist on other models only", () => {
    // Trailhunter is a Tacoma/4Runner grade, not a Camry one.
    const r = SubmissionPayload.safeParse({ ...VALID, trims: ["SE", "Trailhunter"] });
    expect(r.success).toBe(false);
    expect(r.error?.issues[0]?.message).toMatch(/no "Trailhunter" trim/);
  });

  it("rejects colors not offered on the selected trims", () => {
    // Wind Chill Pearl is a Camry color, but not on the Nightshade grade.
    const r = SubmissionPayload.safeParse({
      ...VALID,
      trims: ["Nightshade"],
      colors: ["Wind Chill Pearl"],
    });
    expect(r.success).toBe(false);
    expect(r.error?.issues[0]?.message).toMatch(/not offered on Camry Nightshade/);
  });

  it("accepts a color offered on only one of several selected trims", () => {
    const r = SubmissionPayload.safeParse({
      ...VALID,
      trims: ["Nightshade", "XLE"],
      colors: ["Wind Chill Pearl"], // XLE offers it, Nightshade doesn't
    });
    expect(r.success).toBe(true);
  });
});
