"""Per-dealership negotiation StateGraph.

One thread per dealership, keyed by negotiation_id. The graph is compiled
without a checkpointer here; api/app.py recompiles it with the appropriate
saver (SQLite in dev, Postgres in prod) during the FastAPI lifespan.
"""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from car_agent.nodes.negotiation_v2 import (
    advance_or_end,
    classify_reply_node,
    draft_stage_email_node,
    queue_for_review_node,
    route_after_approval,
    wait_for_approval_node,
    wait_for_dealer_reply_node,
)
from car_agent.state import NegotiationState

builder = StateGraph(NegotiationState)

builder.add_node("draft_stage_email", draft_stage_email_node)
builder.add_node("queue_for_review", queue_for_review_node)
builder.add_node("wait_for_approval", wait_for_approval_node)
builder.add_node("wait_for_dealer_reply", wait_for_dealer_reply_node)
builder.add_node("classify_reply", classify_reply_node)

builder.set_entry_point("draft_stage_email")
builder.add_edge("draft_stage_email", "queue_for_review")
builder.add_edge("queue_for_review", "wait_for_approval")
builder.add_conditional_edges(
    "wait_for_approval",
    route_after_approval,
    {"wait_for_dealer_reply": "wait_for_dealer_reply", END: END},
)
builder.add_edge("wait_for_dealer_reply", "classify_reply")
builder.add_conditional_edges(
    "classify_reply",
    advance_or_end,
    {"draft_stage_email": "draft_stage_email", END: END},
)
