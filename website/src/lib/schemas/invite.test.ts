import { describe, it, expect } from "vitest";
import { InviteCodePayload, normalizeInviteCode } from "./invite";

describe("normalizeInviteCode", () => {
  // Must stay in lockstep with the agent's invite_repo.normalize_code.
  it.each([
    ["DALE-7K3M", "DALE-7K3M"],
    ["dale-7k3m", "DALE-7K3M"],
    ["dale7k3m", "DALE-7K3M"],
    ["DALE 7K3M", "DALE-7K3M"],
    ["7k3m", "DALE-7K3M"],
    ["  7K3M  ", "DALE-7K3M"],
  ])("normalizes %s", (raw, expected) => {
    expect(normalizeInviteCode(raw)).toBe(expected);
  });

  it.each([
    [""],
    ["DALE"],
    ["DALE-7K3"],
    ["DALE-7K3MM"],
    ["DALE-70IM"], // 0 and I are excluded from the alphabet
    ["not a code"],
    ["DALE-7K3M-92XQ"],
  ])("rejects %s", (raw) => {
    expect(normalizeInviteCode(raw)).toBeNull();
  });
});

describe("InviteCodePayload", () => {
  it("accepts a non-empty code", () => {
    expect(InviteCodePayload.safeParse({ code: "DALE-7K3M" }).success).toBe(true);
  });

  it("rejects an empty code", () => {
    expect(InviteCodePayload.safeParse({ code: "  " }).success).toBe(false);
  });
});
