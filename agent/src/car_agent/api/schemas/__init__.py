"""HTTP request/response schemas, one module per resource.

Schemas live here (not under `api/routes/`) so route modules stay focused on
HTTP wiring. Each resource module exports its `*Request` and `*Response`
models. Internal services should accept domain entities, not these schemas.
"""

from car_agent.api.schemas.analyze import AnalyzeRequest, AnalyzeResponse
from car_agent.api.schemas.invites import RedeemInviteRequest, RedeemInviteResponse
from car_agent.api.schemas.negotiate import NegotiateRequest, NegotiateResponse
from car_agent.api.schemas.results import ResultsResponse
from car_agent.api.schemas.reviews import (
    ApproveResponse,
    CancelRequest,
    CancelResponse,
    ReviewDetail,
    ReviewListResponse,
    ReviewSummary,
    SendOutcome,
)

__all__ = [
    "AnalyzeRequest",
    "AnalyzeResponse",
    "ApproveResponse",
    "CancelRequest",
    "CancelResponse",
    "NegotiateRequest",
    "NegotiateResponse",
    "RedeemInviteRequest",
    "RedeemInviteResponse",
    "ResultsResponse",
    "ReviewDetail",
    "ReviewListResponse",
    "ReviewSummary",
    "SendOutcome",
]
