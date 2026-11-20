/** Typed error envelope shared across all route handlers. */

import { NextResponse } from "next/server";

export type ErrorCode =
  | "VALIDATION_ERROR"
  | "UPSTREAM_ERROR"
  | "NOT_FOUND"
  | "INTERNAL_ERROR"
  | "INVITE_REQUIRED"
  | "RATE_LIMITED";

export type AppError = {
  code: ErrorCode;
  message: string;
};

export type ErrorEnvelope = {
  error: AppError;
};

export function errorResponse(
  code: ErrorCode,
  message: string,
  status: number
): NextResponse<ErrorEnvelope> {
  return NextResponse.json({ error: { code, message } }, { status });
}
