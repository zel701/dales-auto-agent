"""/api/reviews — list, fetch, approve, retry, cancel HITL packets.

All routes require the `X-Review-Token` header to match the `REVIEW_API_TOKEN`
env var. The website is the only intended caller; it sets the header
server-side from its own env so the token never reaches the browser.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Query

from car_agent.api.schemas import (
    ApproveResponse,
    CancelRequest,
    CancelResponse,
    ReviewDetail,
    ReviewListResponse,
    ReviewSummary,
    SendOutcome,
)
from car_agent.clients.email import send_email
from car_agent.db.models.review_checkpoint import ReviewCheckpoint
from car_agent.db.repositories.review_checkpoint_repo import (
    finalize_checkpoint,
    get_checkpoint,
    list_checkpoints,
    replace_email_payload,
)
from car_agent.logging_config import neg_id_var
from car_agent.services.email_templates import wrap_analysis_email
from car_agent.services.llm.analysis import generate_analysis_email
from car_agent.services.review_delivery import EmailDeliveryFailed, require_delivery

logger = logging.getLogger(__name__)

router = APIRouter()

WEBSITE_URL = os.environ.get("WEBSITE_URL", "http://localhost:3000")


async def _resume_graph(
    thread_id: str, payload: dict, *, expect_waiting_for: str | None = None
) -> bool:
    """Resume a paused negotiation graph thread.

    Returns True if the resume ran and (when ``expect_waiting_for`` is given) the
    thread parked at the expected interrupt. A silent failure here previously
    stranded threads at the approval interrupt, so failures are logged loudly —
    but not raised, since the checkpoint is already finalized by the time we
    resume. We verify on the pending interrupt's marker rather than ``state.next``,
    which is unreliable for loop interrupts.
    """
    try:
        from langgraph.types import Command

        from car_agent.api.app import graph
        from car_agent.graph_state import pending_interrupt_marker

        config = {"configurable": {"thread_id": thread_id}}
        await graph.ainvoke(Command(resume=payload), config)
        state = await graph.aget_state(config)
        marker = pending_interrupt_marker(state)
        if expect_waiting_for is not None and marker != expect_waiting_for:
            logger.error(
                "Resumed thread %s but it is not waiting for %s (marker=%s); "
                "negotiation may be stranded and dealer replies will not progress",
                thread_id, expect_waiting_for, marker,
            )
            return False
        logger.info("Resumed graph thread %s (waiting_for=%s)", thread_id, marker)
        return True
    except Exception:
        logger.exception("Failed to resume graph thread %s", thread_id)
        return False


def _check_token(token: Optional[str]) -> None:
    expected = os.environ.get("REVIEW_API_TOKEN", "")
    if not expected:
        # Refuse to operate without a configured token — fail closed.
        raise HTTPException(status_code=503, detail="Review token not configured")
    if token != expected:
        raise HTTPException(status_code=401, detail="Invalid review token")


def _to_summary(row: ReviewCheckpoint) -> ReviewSummary:
    return ReviewSummary(
        id=row.id,
        kind=row.kind,
        status=row.status,
        title=row.title,
        customer_email=row.customer.email,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _to_detail(row: ReviewCheckpoint) -> ReviewDetail:
    return ReviewDetail(
        id=row.id,
        kind=row.kind,
        status=row.status,
        title=row.title,
        customer_email=row.customer.email,
        search_result_id=row.search_result_id,
        payload=row.payload,
        result=row.result,
        actor=row.actor,
        created_at=row.created_at,
        updated_at=row.updated_at,
        acted_at=row.acted_at,
    )


@router.get("/api/reviews", response_model=ReviewListResponse)
async def list_reviews(
    status: Optional[str] = Query(default="pending"),
    x_review_token: Optional[str] = Header(default=None, alias="X-Review-Token"),
) -> ReviewListResponse:
    _check_token(x_review_token)
    rows = await list_checkpoints(status=status if status != "all" else None)
    return ReviewListResponse(items=[_to_summary(r) for r in rows])


@router.get("/api/reviews/{checkpoint_id}", response_model=ReviewDetail)
async def get_review(
    checkpoint_id: str,
    x_review_token: Optional[str] = Header(default=None, alias="X-Review-Token"),
) -> ReviewDetail:
    _check_token(x_review_token)
    row = await get_checkpoint(checkpoint_id)
    if not row:
        raise HTTPException(status_code=404, detail="Checkpoint not found")
    return _to_detail(row)


@router.post("/api/reviews/{checkpoint_id}/approve", response_model=ApproveResponse)
async def approve_review(
    checkpoint_id: str,
    x_review_token: Optional[str] = Header(default=None, alias="X-Review-Token"),
) -> ApproveResponse:
    _check_token(x_review_token)
    row = await get_checkpoint(checkpoint_id)
    if not row:
        raise HTTPException(status_code=404, detail="Checkpoint not found")
    if row.status != "pending":
        raise HTTPException(status_code=409, detail=f"Already {row.status}")

    # Informational escalation checkpoints have no email to send and no graph thread to
    # resume — "approve" just acknowledges that a human has handled it.
    if row.kind == "human_review_needed":
        finalized = await finalize_checkpoint(
            id=checkpoint_id, status="approved", actor="reviewer", result=None
        )
        if finalized is None:
            raise HTTPException(status_code=409, detail="Checkpoint already finalized")
        logger.info("Acknowledged human-review checkpoint", extra={"checkpoint_id": checkpoint_id})
        return ApproveResponse(
            success=True,
            send_result=SendOutcome(success=True, dry_run=False),
        )

    email = row.payload.get("email", {})
    graph_meta = row.payload.get("graph", {})
    neg_id = email.get("negotiation_id") or graph_meta.get("negotiation_id")
    if neg_id:
        # Tag the send + finalize + resume logs below with the negotiation.
        neg_id_var.set(neg_id)

    try:
        send_result = await require_delivery(send_email(
            to_email=email.get("to") or row.customer.email,
            subject=email.get("subject", ""),
            body=email.get("full_html", ""),
            html=True,
            negotiation_id=neg_id,
            in_reply_to=email.get("in_reply_to"),
            references=email.get("references"),
        ))
    except EmailDeliveryFailed as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    actor = "reviewer"  # single-reviewer model; cookie identity layer is in front
    finalized = await finalize_checkpoint(
        id=checkpoint_id,
        status="approved",
        actor=actor,
        result={
            "send_success": send_result.success,
            "dry_run": send_result.dry_run,
            "message_id": send_result.message_id,
            "error": send_result.error,
        },
    )
    if finalized is None:
        # Lost a race with another approve/cancel.
        raise HTTPException(status_code=409, detail="Checkpoint already finalized")

    logger.info(
        "Approved checkpoint",
        extra={
            "checkpoint_id": checkpoint_id,
            "send_success": send_result.success,
            "dry_run": send_result.dry_run,
        },
    )

    # Resume the negotiation graph if this was a stage email checkpoint. The
    # thread must advance to wait_for_dealer_reply so the dealer's reply webhook
    # can later progress it; if it doesn't, surface that loudly.
    thread_id = graph_meta.get("thread_id")
    if thread_id:
        resumed = await _resume_graph(
            thread_id=thread_id,
            payload={"approved": True, "message_id": send_result.message_id},
            expect_waiting_for="dealer_reply",
        )
        if not resumed:
            logger.error(
                "Negotiation %s: approval resume did not park at wait_for_dealer_reply; "
                "dealer replies will not advance until repaired",
                neg_id,
            )

    return ApproveResponse(
        success=True,
        send_result=SendOutcome(
            success=send_result.success,
            dry_run=send_result.dry_run,
            error=send_result.error,
            message_id=send_result.message_id,
        ),
    )


@router.post("/api/reviews/{checkpoint_id}/retry", response_model=ReviewDetail)
async def retry_review(
    checkpoint_id: str,
    x_review_token: Optional[str] = Header(default=None, alias="X-Review-Token"),
) -> ReviewDetail:
    _check_token(x_review_token)
    row = await get_checkpoint(checkpoint_id)
    if not row:
        raise HTTPException(status_code=404, detail="Checkpoint not found")
    if row.status != "pending":
        raise HTTPException(status_code=409, detail=f"Cannot retry {row.status}")
    if row.kind != "initial_strategy_email":
        raise HTTPException(
            status_code=400,
            detail=f"Retry not supported for kind '{row.kind}'",
        )

    car_info = row.payload["car_info"]
    listings = row.payload["listings"]
    num_found = row.payload.get("num_found", len(listings))

    redrafted = await generate_analysis_email(
        car_info=car_info,
        listings=listings,
        num_found=num_found,
    )
    results_url = f"{WEBSITE_URL}/results/{row.search_result_id}"
    full_html = wrap_analysis_email(redrafted.html_body, car_info, results_url)

    updated = await replace_email_payload(
        id=checkpoint_id,
        email={
            "to": row.customer.email,
            "subject": redrafted.subject,
            "html_body": redrafted.html_body,
            "full_html": full_html,
        },
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="Checkpoint not found")

    logger.info("Redrafted checkpoint", extra={"checkpoint_id": checkpoint_id})
    return _to_detail(updated)


@router.post("/api/reviews/{checkpoint_id}/cancel", response_model=CancelResponse)
async def cancel_review(
    checkpoint_id: str,
    body: CancelRequest | None = None,
    x_review_token: Optional[str] = Header(default=None, alias="X-Review-Token"),
) -> CancelResponse:
    _check_token(x_review_token)
    row = await get_checkpoint(checkpoint_id)
    if not row:
        raise HTTPException(status_code=404, detail="Checkpoint not found")
    if row.status != "pending":
        raise HTTPException(status_code=409, detail=f"Already {row.status}")

    reason = body.reason if body else None
    graph_meta = row.payload.get("graph", {})
    neg_id = graph_meta.get("negotiation_id") or graph_meta.get("thread_id")
    if neg_id:
        neg_id_var.set(neg_id)

    finalized = await finalize_checkpoint(
        id=checkpoint_id,
        status="cancelled",
        actor="reviewer",
        result={"reason": reason} if reason else None,
    )
    if finalized is None:
        raise HTTPException(status_code=409, detail="Checkpoint already finalized")
    logger.info("Cancelled checkpoint", extra={"checkpoint_id": checkpoint_id})

    thread_id = graph_meta.get("thread_id")
    if thread_id:
        await _resume_graph(thread_id=thread_id, payload={"approved": False, "reason": reason})

    return CancelResponse(success=True)
