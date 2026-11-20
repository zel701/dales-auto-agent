"""Graph nodes for the per-dealership 5-stage negotiation flow."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import uuid4

from langgraph.graph import END
from langgraph.types import interrupt

from car_agent.db.repositories.review_checkpoint_repo import create_checkpoint
from car_agent.services.llm.negotiation_stages import (
    classify_stage_reply,
    draft_stage_email,
)
from car_agent.state import EmailMessage, NegotiationState

logger = logging.getLogger(__name__)

_UTC = timezone.utc

# Max polite re-asks at a single stage when the dealer deflects (invites in-person /
# test drive instead of answering) before escalating to human review.
MAX_REASKS = 2


# ---------------------------------------------------------------------------
# Draft the outbound email for the current stage
# ---------------------------------------------------------------------------


async def draft_stage_email_node(state: NegotiationState) -> dict:
    is_reask = state.get("reask_count", 0) > 0
    draft = await draft_stage_email(
        stage=state["current_stage"],
        dealership=state["dealership"],
        cars=state["dealership"]["cars"],
        customer_name=state["customer"].get("name"),
        thread=list(state["thread"]),
        stage_data=state["stage_data"],
        is_reask=is_reask,
    )
    logger.info(
        "Drafted stage %d email",
        state["current_stage"],
        extra={
            "stage": state["current_stage"],
            "order_id": state["order_id"],
            "is_reask": is_reask,
            "subject": draft.subject,
            "body": draft.body,
        },
    )
    return {
        "draft_subject": draft.subject,
        "draft_body": draft.body,
    }


# ---------------------------------------------------------------------------
# Queue the draft for HITL review
# ---------------------------------------------------------------------------


async def queue_for_review_node(state: NegotiationState) -> dict:
    neg_id = state["negotiation_id"]
    stage = state["current_stage"]
    dealer = state["dealership"]
    body = state["draft_body"] or ""

    # The first outbound email establishes the thread subject; every later one
    # is sent as "Re: {it}" with In-Reply-To/References so mail clients keep
    # the whole negotiation in a single thread.
    thread_subject = state.get("thread_subject")
    if thread_subject:
        subject = f"Re: {thread_subject}"
    else:
        subject = state["draft_subject"] or f"Stage {stage} — {dealer['dealer_name']}"
        thread_subject = subject

    checkpoint_id = str(uuid4())
    await create_checkpoint(
        id=checkpoint_id,
        kind="negotiation_stage_email",
        customer_id=state["customer"]["db_id"],
        title=f"Stage {stage} Email — {dealer['dealer_name']}",
        payload={
            "email": {
                "to": dealer.get("dealer_email") or "",
                "subject": subject,
                "html_body": body,
                "full_html": body,
                "negotiation_id": neg_id,
                "in_reply_to": state.get("last_inbound_message_id"),
                "references": list(state.get("references") or []),
            },
            "graph": {
                "thread_id": neg_id,
                "negotiation_id": neg_id,
                "stage": stage,
            },
        },
    )

    outbound: EmailMessage = {
        "direction": "outbound",
        "subject": subject,
        "body": body,
        "timestamp": datetime.now(_UTC).isoformat(),
        "stage": stage,
    }

    logger.info(
        "Queued stage %d email for negotiation %s (checkpoint %s)",
        stage, neg_id, checkpoint_id,
    )
    return {
        "pending_checkpoint_id": checkpoint_id,
        "thread": [outbound],
        "thread_subject": thread_subject,
    }


# ---------------------------------------------------------------------------
# Pause until reviewer approves or cancels
# ---------------------------------------------------------------------------


async def wait_for_approval_node(state: NegotiationState) -> dict:
    # Loop so an unexpected resume (e.g. a dealer reply mis-routed to this
    # interrupt) can't be silently read as a rejection and kill the negotiation.
    # Only an explicit decision dict ({"approved": bool}) is accepted.
    while True:
        result = interrupt({
            "waiting_for": "approval",
            "checkpoint_id": state["pending_checkpoint_id"],
        })
        if isinstance(result, dict) and "approved" in result:
            break
        logger.warning(
            "Negotiation %s stage %d: ignoring unexpected approval resume %r; re-waiting",
            state["negotiation_id"], state["current_stage"], result,
        )

    if not result["approved"]:
        logger.info("Negotiation %s stage %d cancelled by reviewer", state["negotiation_id"], state["current_stage"])
        return {"status": "stalled"}
    return {}


def route_after_approval(state: NegotiationState) -> str:
    if state["status"] != "in_progress":
        return END
    return "wait_for_dealer_reply"


# ---------------------------------------------------------------------------
# Pause until the dealer replies (resumed by the Resend inbound webhook)
# ---------------------------------------------------------------------------


async def wait_for_dealer_reply_node(state: NegotiationState) -> dict:
    result = interrupt({
        "waiting_for": "dealer_reply",
        "negotiation_id": state["negotiation_id"],
        "stage": state["current_stage"],
    })

    # The webhook resumes with {body, message_id, subject}; a bare string is
    # still accepted for manual replays and threads suspended pre-upgrade.
    if isinstance(result, dict):
        reply_body = str(result.get("body") or "")
        message_id = result.get("message_id")
        reply_subject = result.get("subject")
    else:
        reply_body = str(result)
        message_id = None
        reply_subject = None

    logger.info(
        "Dealer reply received at stage %d",
        state["current_stage"],
        extra={
            "stage": state["current_stage"],
            "order_id": state["order_id"],
            "reply_body": reply_body,
            "message_id": message_id,
        },
    )

    inbound: EmailMessage = {
        "direction": "inbound",
        "subject": reply_subject,
        "body": reply_body,
        "timestamp": datetime.now(_UTC).isoformat(),
        "stage": state["current_stage"],
    }

    references = list(state.get("references") or [])
    if message_id:
        references.append(message_id)
    return {
        "thread": [inbound],
        "last_inbound_message_id": message_id or state.get("last_inbound_message_id"),
        "references": references,
    }


# ---------------------------------------------------------------------------
# Classify the dealer reply and advance the stage
# ---------------------------------------------------------------------------


async def _escalate_to_human(state: NegotiationState, stage: int, dealer_reply: str) -> None:
    """Flag a stuck negotiation for human review via a pending checkpoint.

    Surfaced in the existing /api/reviews list (pull-based; no push notification).
    Carries no email payload or graph thread_id, so approve_review must not try to
    send an email or resume the graph for this kind.
    """
    dealer = state["dealership"]
    checkpoint_id = str(uuid4())
    await create_checkpoint(
        id=checkpoint_id,
        kind="human_review_needed",
        customer_id=state["customer"]["db_id"],
        title=f"Human review — {dealer['dealer_name']} stuck at stage {stage}",
        payload={
            "negotiation_id": state["negotiation_id"],
            "order_id": state["order_id"],
            "stage": stage,
            "dealer_name": dealer["dealer_name"],
            "dealer_reply": dealer_reply,
            "reason": (
                f"Dealer repeatedly deflected (invited in-person visit / test drive) at "
                f"stage {stage} without answering, after {MAX_REASKS} polite re-asks."
            ),
        },
    )


async def classify_reply_node(state: NegotiationState) -> dict:
    thread = state["thread"]
    inbound_msgs = [m for m in thread if m["direction"] == "inbound"]
    if not inbound_msgs:
        return {"status": "stalled"}

    latest_body = inbound_msgs[-1]["body"]
    stage = state["current_stage"]

    outcome = await classify_stage_reply(
        stage=stage,
        dealer_reply=latest_body,
        stage_data=state["stage_data"],
        cars=state["dealership"]["cars"],
    )

    logger.info(
        "Classified stage %d reply (advance=%s)",
        stage, outcome.get("advance"),
        extra={
            "stage": stage,
            "order_id": state["order_id"],
            "input_email": latest_body,
            "decision": outcome,
            "advance": outcome.get("advance", False),
        },
    )

    new_stage_data = dict(state["stage_data"])
    new_stage_data[str(stage)] = outcome

    # Advance: the dealer provided what we asked for. Reset the re-ask counter.
    if outcome.get("advance", False):
        next_stage = stage + 1
        if stage >= 5:
            logger.info("Negotiation %s completed all 5 stages", state["negotiation_id"])
            return {
                "stage_data": new_stage_data,
                "current_stage": next_stage,
                "status": "appointment_set",
                "reask_count": 0,
            }
        logger.info("Negotiation %s advancing from stage %d to %d", state["negotiation_id"], stage, next_stage)
        return {"stage_data": new_stage_data, "current_stage": next_stage, "reask_count": 0}

    # Deflection (stages 1-3): dealer invited an in-person visit/test drive instead of
    # answering. Politely re-ask the same stage up to MAX_REASKS, then escalate.
    reask_count = state.get("reask_count", 0)
    if outcome.get("deflected", False) and stage in (1, 2, 3):
        if reask_count < MAX_REASKS:
            new_count = reask_count + 1
            logger.info(
                "Negotiation %s re-asking stage %d (deflection %d/%d)",
                state["negotiation_id"], stage, new_count, MAX_REASKS,
                extra={"stage": stage, "order_id": state["order_id"], "reask_count": new_count},
            )
            # status stays in_progress and current_stage is unchanged, so advance_or_end
            # routes back to draft_stage_email for the same stage (as a re-ask).
            return {"stage_data": new_stage_data, "reask_count": new_count}

        await _escalate_to_human(state, stage, latest_body)
        logger.warning(
            "Negotiation %s escalated to human review at stage %d after %d deflections",
            state["negotiation_id"], stage, reask_count,
            extra={"stage": stage, "order_id": state["order_id"]},
        )
        return {"stage_data": new_stage_data, "status": "needs_human"}

    # Non-deflection non-advance: dead end (e.g. flat refusal). Stall, as before.
    logger.info("Negotiation %s stage %d did not advance", state["negotiation_id"], stage)
    return {"stage_data": new_stage_data, "status": "stalled"}


def advance_or_end(state: NegotiationState) -> str:
    if state["status"] != "in_progress":
        return END
    return "draft_stage_email"
