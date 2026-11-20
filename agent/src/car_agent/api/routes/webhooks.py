"""POST /resend/inbound — handle inbound dealer reply emails from Resend."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request
from langgraph.types import Command

from car_agent.clients.resend_inbound import fetch_email_body, verify_webhook
from car_agent.db.repositories.inbound_event_repo import is_processed, mark_processed
from car_agent.graph_state import pending_interrupt_marker
from car_agent.logging_config import neg_id_var
from car_agent.services.webhook_routing import extract_negotiation_id, get_thread_id

logger = logging.getLogger(__name__)

router = APIRouter()


def _awaiting_dealer_reply(state) -> bool:
    """True if the graph thread is suspended at the wait_for_dealer_reply interrupt.

    A thread has at most one pending interrupt. We must only resume a thread that
    is actually waiting for a dealer reply — resuming a thread parked at the HITL
    approval interrupt would feed the email body into the wrong interrupt and
    silently stall the negotiation.
    """
    return pending_interrupt_marker(state) == "dealer_reply"


@router.post("/resend/inbound")
async def resend_inbound(request: Request):
    """Handle inbound email events from Resend.

    Resend POSTs a JSON event with metadata only; we fetch the email body
    separately via resend.Emails.Receiving.get(email_id=...).

    Flow:
    1. Verify Svix webhook signature.
    2. Deduplicate by event id.
    3. Extract negotiation_id from the deals+{id}@domain recipient address.
    4. Look up the LangGraph thread_id.
    5. Fetch the email body from Resend.
    6. Resume the graph thread with the dealer's reply.
    """
    from car_agent.api.app import graph

    raw_body = await request.body()
    headers = dict(request.headers)

    if not verify_webhook(raw_body, headers):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    try:
        import json
        event = json.loads(raw_body)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    if event.get("type") != "email.received":
        return {"status": "ignored", "reason": "not email.received"}

    data = event.get("data", {})
    event_id = event.get("id") or data.get("email_id") or ""

    if not event_id:
        return {"status": "ignored", "reason": "no event id"}

    if await is_processed(event_id):
        logger.info("Duplicate Resend event %s; ignoring", event_id)
        return {"status": "duplicate"}

    # Extract negotiation_id from recipient address
    recipients = data.get("to") or []
    negotiation_id = None
    for addr in recipients:
        negotiation_id = extract_negotiation_id(addr)
        if negotiation_id:
            break

    if not negotiation_id:
        await mark_processed(event_id)
        return {"status": "ignored", "reason": "no negotiation_id in recipient"}

    # Tag all log lines for this resume (incl. graph node logs) with the negotiation.
    neg_id_var.set(negotiation_id)

    thread_id = await get_thread_id(negotiation_id)
    if not thread_id:
        # Don't 4xx — Resend retries on non-2xx and we'd loop forever.
        logger.warning("Unknown negotiation_id %s from Resend event %s", negotiation_id, event_id)
        await mark_processed(event_id)
        return {"status": "ignored", "reason": "unknown negotiation_id"}

    # Only resume a thread that is actually waiting for a dealer reply. If the
    # thread is parked at the approval interrupt, already finished, or has no
    # pending interrupt, resuming would corrupt that other interrupt's state.
    config = {"configurable": {"thread_id": thread_id}}
    state = await graph.aget_state(config)
    if not _awaiting_dealer_reply(state):
        logger.warning(
            "Negotiation %s (thread %s) is not awaiting a dealer reply (next=%s); "
            "not resuming. Reply not applied — requires manual replay.",
            negotiation_id, thread_id, state.next,
        )
        # 2xx so Resend doesn't retry-loop; left un-marked so a later manual
        # replay isn't blocked by dedup.
        return {"status": "ignored", "reason": "thread not awaiting dealer reply"}

    # Resend's inbound webhook is metadata-only, so fetch the body via the API.
    # The inline text/html branches are defensive only.
    body = data.get("text") or ""
    if not body:
        from car_agent.clients.resend_inbound import _strip_html
        body = _strip_html(data.get("html") or "").strip()
    if not body:
        email_id = data.get("email_id") or ""
        body = await fetch_email_body(email_id) if email_id else ""
    if not body:
        body = data.get("subject") or "(empty reply)"

    await mark_processed(event_id)

    # Include the RFC Message-ID and subject so outbound follow-ups can be sent
    # as replies in the same email thread (In-Reply-To / References headers).
    resume_payload = {
        "body": body,
        "message_id": data.get("message_id"),
        "subject": data.get("subject"),
    }

    try:
        await graph.ainvoke(Command(resume=resume_payload), config)
        logger.info("Resumed negotiation %s (thread %s) with dealer reply", negotiation_id, thread_id)
    except Exception:
        logger.exception("Error resuming negotiation %s", negotiation_id)
        return {"status": "error"}

    return {"status": "ok", "negotiation_id": negotiation_id}
