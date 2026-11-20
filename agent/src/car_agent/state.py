"""LangGraph state schemas for the per-dealership negotiation flow."""

from __future__ import annotations

import operator
from typing import Annotated, Literal, Optional

from typing_extensions import TypedDict


class CustomerCtx(TypedDict):
    db_id: str
    name: Optional[str]
    email: str
    phone: Optional[str]


class DealershipGroup(TypedDict):
    dealer_key: str        # normalized dealer name used as a dedup key
    dealer_name: str
    dealer_email: Optional[str]
    dealer_phone: Optional[str]
    cars: list[dict]       # raw listing dicts from Order.selected_listings


class EmailMessage(TypedDict):
    direction: Literal["outbound", "inbound"]
    subject: Optional[str]
    body: str
    timestamp: str         # ISO 8601
    stage: int


class NegotiationState(TypedDict):
    negotiation_id: str    # uuid; doubles as the LangGraph thread_id
    order_id: str
    customer: CustomerCtx
    dealership: DealershipGroup
    current_stage: int     # 1..5
    thread: Annotated[list[EmailMessage], operator.add]
    pending_checkpoint_id: Optional[str]
    draft_subject: Optional[str]
    draft_body: Optional[str]
    stage_data: dict       # {stage_int: {outcome_fields…}}
    reask_count: int       # consecutive polite re-asks at current_stage; reset on advance
    thread_subject: Optional[str]           # subject of the first outbound; later stages send "Re: {it}"
    last_inbound_message_id: Optional[str]  # RFC Message-ID of the latest dealer reply
    references: list[str]                   # dealer Message-IDs accumulated for the References header
    status: Literal["in_progress", "appointment_set", "stalled", "unavailable", "needs_human"]
