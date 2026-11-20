"""Sample data and isolated negotiation state for the public demo."""

import asyncio
from functools import partial
from time import monotonic
from typing import Literal
from uuid import uuid4

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command
from pydantic import BaseModel

from car_agent.clients.email import EmailResult
from car_agent.graph import build_negotiation_graph
from car_agent.graph_state import pending_interrupt_marker
from car_agent.nodes.negotiation_v2 import (
    classify_reply_node,
    draft_stage_email_node,
    queue_for_review_node,
)
from car_agent.services.llm.negotiation_stages import EmailDraft
from car_agent.services.review_delivery import EmailDeliveryFailed, require_delivery
from car_agent.state import NegotiationState

SESSION_TTL = 30 * 60
VIN = "4T1DAACK0TU000001"
APPOINTMENT = "Saturday at 10:00 AM"

DRAFTS = (
    f"Hi, I'm a buyer's agent. Is the 2026 Camry LE (VIN {VIN}) still available?",
    "Thanks for confirming. Could you share the itemized out-the-door price, including taxes and fees?",
    "Could you offer a vehicle price of $27,300 before taxes and fees?",
    "Thanks for agreeing to the price. What time this weekend works for an appointment?",
    f"{APPOINTMENT} works. Please confirm the appointment.",
)
REPLIES = (
    "Yes, the Camry LE is in stock and available.",
    "Our out-the-door price is $32,000: $29,950 for the vehicle and $2,050 in taxes and fees.",
    "We can sell the vehicle for $27,300 before taxes and fees.",
    f"We can meet {APPOINTMENT}.",
    f"Confirmed for {APPOINTMENT} at Demo Toyota.",
)
OUTCOMES = (
    {"available_vins": [VIN], "unavailable_vins": []},
    {"otd_total": 32000, "has_breakdown": True},
    {"target_met": True, "agreed_price": 27300},
    {"proposed_times": [APPOINTMENT]},
    {"confirmed": True, "confirmed_time": APPOINTMENT},
)


async def sample_draft(*, stage: int, **_kwargs) -> EmailDraft:
    return EmailDraft(subject="2026 Toyota Camry LE inquiry", body=DRAFTS[stage - 1])


async def sample_classification(*, stage: int, dealer_reply: str, **_kwargs) -> dict:
    if dealer_reply != REPLIES[stage - 1]:
        return {"advance": False}
    return {"advance": True, **OUTCOMES[stage - 1]}


class DemoState(BaseModel):
    revision: int
    stage: int
    status: Literal["approval", "dealer_reply", "appointment_set", "stalled"]
    subject: str
    draft: str
    latest_reply: str | None = None
    appointment: str | None = None
    error: str | None = None


DemoAction = Literal["send", "reply", "restart"]


class DemoSession:
    def __init__(self):
        self.lock = asyncio.Lock()
        self.expires_at = monotonic() + SESSION_TTL
        self.revision = 0
        self.first_send = True
        self.error: str | None = None
        self.email: dict = {}

    async def _save_checkpoint(self, *, payload: dict, **_kwargs) -> None:
        self.email = payload.get("email", {})

    async def start(self) -> DemoState:
        self.error = None
        self.first_send = True
        self.email = {}
        thread_id = str(uuid4())
        self.config = {"configurable": {"thread_id": thread_id}}
        self.graph = build_negotiation_graph(
            draft_node=partial(draft_stage_email_node, draft_email=sample_draft),
            queue_node=partial(queue_for_review_node, save_checkpoint=self._save_checkpoint),
            classify_node=partial(
                classify_reply_node,
                classify_reply=sample_classification,
                save_checkpoint=self._save_checkpoint,
            ),
        ).compile(checkpointer=InMemorySaver())
        state: NegotiationState = {
            "negotiation_id": thread_id,
            "order_id": f"demo-{thread_id}",
            "customer": {"db_id": thread_id, "name": "Demo Buyer", "email": "buyer@example.com", "phone": None},
            "dealership": {
                "dealer_key": "demo-toyota", "dealer_name": "Demo Toyota",
                "dealer_email": "dealer@example.com", "dealer_phone": None,
                "cars": [{"vin": VIN, "year": 2026, "make": "Toyota", "model": "Camry", "trim": "LE", "price": 29950}],
            },
            "current_stage": 1,
            "thread": [],
            "pending_checkpoint_id": None,
            "draft_subject": None,
            "draft_body": None,
            "stage_data": {},
            "reask_count": 0,
            "thread_subject": None,
            "last_inbound_message_id": None,
            "references": [],
            "status": "in_progress",
        }
        await self.graph.ainvoke(state, self.config)
        return await self.state()

    async def state(self) -> DemoState:
        snapshot = await self.graph.aget_state(self.config)
        values = snapshot.values
        status = pending_interrupt_marker(snapshot)
        if status is None:
            status = "appointment_set" if values["status"] == "appointment_set" else "stalled"
        latest_reply = next(
            (message["body"] for message in reversed(values["thread"]) if message["direction"] == "inbound"),
            None,
        )
        return DemoState(
            revision=self.revision,
            stage=min(values["current_stage"], len(DRAFTS)),
            status=status,
            subject=self.email.get("subject", ""),
            draft=self.email.get("full_html", ""),
            latest_reply=latest_reply,
            appointment=values["stage_data"].get("5", {}).get("confirmed_time"),
            error=self.error,
        )

    async def _deliver(self) -> EmailResult:
        if self.first_send:
            self.first_send = False
            return EmailResult(False, None, True, "The simulated mail provider rejected this attempt.")
        return EmailResult(True, str(uuid4()), True)

    async def act(self, action: DemoAction, revision: int) -> tuple[DemoState, int]:
        current = await self.state()
        required = {"send": "approval", "reply": "dealer_reply"}
        # Serialize each session, and reject stale requests from double clicks or another tab.
        if revision != self.revision or (action in required and current.status != required[action]):
            return current, 409
        self.revision += 1
        self.error = None
        if action == "restart":
            return await self.start(), 200
        if action == "send":
            try:
                result = await require_delivery(self._deliver())
            except EmailDeliveryFailed as exc:
                self.error = str(exc)
                return await self.state(), 502
            resume = {"approved": True, "message_id": result.message_id}
        else:
            resume = {
                "body": REPLIES[current.stage - 1],
                "subject": f"Re: {current.subject.removeprefix('Re: ')}",
                "message_id": f"<{uuid4()}@example.com>",
            }
        await self.graph.ainvoke(Command(resume=resume), self.config)
        return await self.state(), 200
