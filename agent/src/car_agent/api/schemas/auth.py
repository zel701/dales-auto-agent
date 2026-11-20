"""Auth API schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class RequestOtpRequest(BaseModel):
    email: str = Field(min_length=3, max_length=200)


class RequestOtpResponse(BaseModel):
    ok: bool = True


class VerifyOtpRequest(BaseModel):
    email: str = Field(min_length=3, max_length=200)
    code: str = Field(min_length=6, max_length=6)


class CustomerSummary(BaseModel):
    id: str
    email: str


class VerifyOtpResponse(BaseModel):
    customer: CustomerSummary


class MeResponse(BaseModel):
    customer: CustomerSummary | None = None


class LogoutResponse(BaseModel):
    ok: bool = True
