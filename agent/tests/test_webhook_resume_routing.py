"""Tests for dealer-reply resume routing and approval-interrupt hardening.

Covers the two correctness fixes:
  * The inbound webhook must only resume a thread that is actually waiting for a
    dealer reply (``_awaiting_dealer_reply``), never one parked at the HITL
    approval interrupt.
  * ``wait_for_approval_node`` must ignore a stray/mis-routed resume instead of
    reading it as a rejection and stalling the negotiation.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import TypedDict

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from car_agent.api.routes.webhooks import _awaiting_dealer_reply
from car_agent.graph_state import pending_interrupt_marker
from car_agent.nodes.negotiation_v2 import wait_for_approval_node


# ---------------------------------------------------------------------------
# _awaiting_dealer_reply — pending-interrupt discriminator
# ---------------------------------------------------------------------------


def _fake_state(*interrupt_values, next_=("node",)):
    interrupts = [SimpleNamespace(value=v) for v in interrupt_values]
    task = SimpleNamespace(interrupts=interrupts)
    return SimpleNamespace(tasks=[task], next=next_)


def test_awaiting_dealer_reply_true_for_dealer_reply_interrupt():
    state = _fake_state({"waiting_for": "dealer_reply", "negotiation_id": "n1", "stage": 1})
    assert _awaiting_dealer_reply(state) is True


def test_awaiting_dealer_reply_false_for_approval_interrupt():
    state = _fake_state({"waiting_for": "approval", "checkpoint_id": "c1"})
    assert _awaiting_dealer_reply(state) is False


def test_awaiting_dealer_reply_false_when_no_pending_interrupt():
    state = SimpleNamespace(tasks=[], next=())
    assert _awaiting_dealer_reply(state) is False


def test_awaiting_dealer_reply_ignores_non_dict_interrupt_values():
    state = _fake_state("just a string")
    assert _awaiting_dealer_reply(state) is False


# ---------------------------------------------------------------------------
# wait_for_approval_node — must not stall on an unexpected resume
# ---------------------------------------------------------------------------


class _ApprovalState(TypedDict, total=False):
    pending_checkpoint_id: str
    negotiation_id: str
    current_stage: int
    status: str


def _approval_graph():
    builder = StateGraph(_ApprovalState)
    builder.add_node("wait_for_approval", wait_for_approval_node)
    builder.add_edge(START, "wait_for_approval")
    builder.add_edge("wait_for_approval", END)
    return builder.compile(checkpointer=InMemorySaver())


_INITIAL: _ApprovalState = {
    "pending_checkpoint_id": "c1",
    "negotiation_id": "n1",
    "current_stage": 1,
    "status": "in_progress",
}


async def test_approval_node_suspends_initially():
    graph = _approval_graph()
    cfg = {"configurable": {"thread_id": "t-suspend"}}
    await graph.ainvoke(_INITIAL, cfg)
    state = await graph.aget_state(cfg)
    # Parked at the approval interrupt (discriminate on the marker, not next,
    # which is unreliable for loop interrupts).
    assert pending_interrupt_marker(state) == "approval"


async def test_approval_node_ignores_mis_routed_dealer_reply():
    graph = _approval_graph()
    cfg = {"configurable": {"thread_id": "t-stray"}}
    await graph.ainvoke(_INITIAL, cfg)

    # A dealer reply (plain string) mis-routed to the approval interrupt must not
    # be read as a rejection: the thread stays suspended, still in_progress.
    await graph.ainvoke(Command(resume="Yes, this car is still available"), cfg)
    state = await graph.aget_state(cfg)
    assert pending_interrupt_marker(state) == "approval"
    assert state.values.get("status") == "in_progress"

    # A real approval then completes it without stalling.
    await graph.ainvoke(Command(resume={"approved": True}), cfg)
    state = await graph.aget_state(cfg)
    assert pending_interrupt_marker(state) is None
    assert state.values.get("status") == "in_progress"


async def test_approval_node_explicit_rejection_stalls():
    graph = _approval_graph()
    cfg = {"configurable": {"thread_id": "t-reject"}}
    await graph.ainvoke(_INITIAL, cfg)

    await graph.ainvoke(Command(resume={"approved": False}), cfg)
    state = await graph.aget_state(cfg)
    assert state.next == ()
    assert state.values.get("status") == "stalled"
